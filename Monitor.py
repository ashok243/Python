import datetime
import urllib.parse
import requests
import json
import time

from functools import reduce
from inspect import cleandoc


"""ServiceNow CR creation module
"""

class CRCreationError(Exception):
    """Raised when http status is other than 200"""


class Authenticator:
    """ServiceNow API authentication helper
    """

    def __init__(self, params):
        """Initialise instance variables
        Args:
            params: dict() -> ServiceNow Authentication parameters
        """
        self.params = params
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}

    def get_token(self):
        """Returns time bound token
        """
        print('BEGIN: Fetching authentication token')
        payload = dict()
        token_data = ""
        try:
            token_url = self.params['url'].split('/api/')[0] + "/oauth_token.do"
            payload['grant_type'] = self.params['auth_grant_type']
            payload['client_id'] = self.params['auth_client_id']
            payload['client_secret'] = self.params['auth_client_secret']
            payload['username'] = self.params['auth_username']
            payload['password'] = self.params['auth_password']
            payload_str='&'.join([k + "=" + urllib.parse.quote(v) for k,v in payload.items()])

            token_data = request_with_retry('POST', token_url, headers=self.headers, data=payload_str)
        except KeyError as ke:
            failstep('Config key - %s doesnt exist' % ke)
        print('END: Fetching authentication token')
        return token_data


class ServiceNowApi:
    """ServiceNow API helper class
    """

    def __init__(self, params):
        """Initialize instance variables
        """
        self.cr_post_url = params['url']
        self.cr_patch_url = params['url'] + "/number"
        self.authenticator = Authenticator(params).get_token()
        self.headers = {
            'Authorization': ' '.join([self.authenticator['token_type'], self.authenticator['access_token']]),
            'content-type': 'application/json'
        }

    def create_change_request(self, data):
        """Method for creating ServiceNow change request
        Args:
            data: dict() -> Change request data dictionary
        Returns:
            cr_number: str -> CR number
        """
        print('BEGIN: Creating change request')
        cr_number = None
        cr_response = None
        cr_description = 'Project Name: {}'.format(data['project_name'])
        if 'web_site_name' in data:
            cr_description += ', WebSiteName: {}'.format(data['web_site_name'])
        if 'release_number' in data:
            cr_description += ', Release Number: {}'.format(data['release_number'])
        if 'release_notes' in data:
            cr_description += ', Release Notes: {}'.format(data['release_notes'])
        change_data = {
            "cmdb_ci": data['cr_cmdb_ci'],
            "u_duration": data['cr_duration'],
            "assigned_to": data['auth_username'],
            "start_date": data['cr_start_date'],
            "justification": cr_description,
            "type": data['cr_type'],
            "state": data['cr_state'], 
            "backout_plan": data['cr_backout_plan'],
            "u_modified_by": "api_octopus",
            "implementation_plan": data['cr_implementation_plan'],
            "test_plan": data['cr_test_plan'],
            "u_impacted_site": "4",
            "u_atb_cust_impact": "0",
            "risk": "low",
            "u_service_category": "Governance_L3 Release Engineering", 
            "u_category_type": "Maintenance", 
            "u_category_subtype": "Software", 
            "u_environment": "production", 
            "assignment_group": "L3 Release Engineering",  
            "short_description": cr_description
        }

        if 'deployment_created_by_username' in data:
            change_data['requested_by'] = data['deployment_created_by_username']
        
        change_data = json.dumps(change_data)
        cr_response = request_with_retry('POST', self.cr_post_url, headers=self.headers, data=change_data)
        if cr_response and 'result' in cr_response:
            result = cr_response['result']
            if 'status' in result and result['status'] == 'success':
                cr_number = result['record_id']
        print('END: Creating change request')
        return cr_number


    def update_change_request(self, data):
        """Method for running patch requests on Change Request
        Args:
            data: dict() -> Change request data dictionary
        """
        print('BEGIN: Updating change request')
        cr_response = None
        is_implemented = False
        change_data = dict()
        
        if 'cr_state' in data:
            change_data['state'] = data['cr_state']

        change_data = json.dumps(change_data)
        cr_response = request_with_retry('PATCH', self.cr_patch_url + "/" + data['cr_number'], headers=self.headers, data=change_data)
        #cr_response = request_with_retry('PATCH', self.cr_patch_url, headers=self.headers, data=change_data)
        if cr_response and 'result' in cr_response:
            result = cr_response['result']
            if 'status' in result and result['status'] == 'success':
                is_implemented = True
        print('END: Updating change request')
        return is_implemented


def load_template(web_site_name, environment_name):
    with open('C:\Script\ServiceNow\Corp-CR-WebSite.json') as template_file:
        tdata = json.load(template_file)

    if web_site_name in tdata:
        if environment_name in tdata[web_site_name]:
            return tdata[web_site_name][environment_name]
        else:
            return tdata[web_site_name]
    else:
        failstep('WebSite: %s is not defined.' % web_site_name)


def request_with_retry(method=None, url=None, headers={}, data=None):
    """Run HTTP requests with upto 3 attempts and waits for 5 secs between each attempt

    Args:
        method: HTTP methods - POST, PATCH etc.
        url: Request URL
        headers: Request headers
        data: Request payload

    Returns:
        response: for successful request
        (or) exit with error
    """
    retry_count = 0
    response = None
    while True:
        try:
            retry_count = retry_count + 1
            response = requests.request(method, url, headers=headers, data=data)
            # Check for HTTP codes other than 200
            if response.status_code >= 400: 
                raise CRCreationError
        except (CRCreationError, requests.exceptions.RequestException):
            if retry_count < 3:
                print('Retrying API - %s operation for URL - %s' % (method, url))
                time.sleep(5)
                continue
            else:
                printwarning('Maximum retries exceeded, exiting..')
                failstep('Status: {}, Headers: {}, Error Response: {}'.format(response.status_code, 
                                                                            response.headers, 
                                                                            response.content))
        break
    return json.loads(response.content, encoding='utf-8')


def read_octopus_vars():
    """Read Octopus variables
    Format:
        ServiceNow.*:           ServiceNow generic variables
        ServiceNow.Auth.*:      ServiceNow authentication parameters
        ServiceNow.Cr.*:        ServiceNow parameters for CR CRUD operations
        Octopus.Deployment.*:   Octopus deployment variables
        Octopus.Release.*:      Octopus release variables
        Octopus.Project.*:      Octopus project variables
    """
    print('BEGIN: Reading octopus variables')
    required_vars = ['ServiceNow.Url', 
                     'ServiceNow.Auth.GrantType', 
                     'ServiceNow.Auth.ClientId',
                     'ServiceNow.Auth.ClientSecret', 
                     'ServiceNow.Auth.Username', 
                     'ServiceNow.Auth.Password',
                     'WebSiteName',
                     'Octopus.Environment.Name',
                     'Octopus.Deployment.CreatedBy.Username',
                     'Octopus.Project.Name']
    optional_vars = ['Octopus.Release.Number',
                     'Octopus.Release.Notes']
    
    def return_if_var_exists(var):
        try:
            return get_octopusvariable(var)
        except Exception as e:
            failstep('Required variable "%s" is not set: %s' % (var, e))

    octopus_vars = {to_snake_case(var): return_if_var_exists(var) for var in required_vars}
    for var in optional_vars:
        if var in octopusvariables and octopusvariables[var]:
            octopus_vars[to_snake_case(var)] = get_octopusvariable(var)
    print('END: Reading octopus variables')
    return octopus_vars


def get_cr_defaults():
    """Return CR defaults for CR creation.
    These are release independent parameters required to move CR into scheduled/implement state
    """
    print('BEGIN: Reading CR defaults')
    cr_defaults = dict()
    cr_defaults['cr_type'] = 'standard'
    cr_defaults['cr_state'] = 'scheduled'
    cr_defaults['cr_duration'] = 180
    cr_defaults['cr_start_date'] = str(datetime.datetime.today() + datetime.timedelta(days=0))
    print('END: Reading CR defaults')
    return cr_defaults


def to_snake_case(camel_str):
    """Convert a given string to snake case

    Args:
        camel_str: str -> Eg: ServiceNow.Cr.Template
    Returns:
        snake_str: str -> Eg: cr_template
    """
    slist = []
    if len(camel_str.split('.')[1:]) > 0:
        slist = camel_str.split('.')[1:]
    else:
        slist = camel_str.split('.')[:]
    slist_snake_case = [reduce(lambda x, y: x + ('_' if y.isupper() else '') + y, var_part).lower() 
                        for var_part in slist]
    return '_'.join(slist_snake_case)


def set_context(octopus_vars=dict(), cr_defaults=dict()):
    """Set deployment context
    """
    print('BEGIN: Setting deployment context')
    for param, val in cr_defaults.items():
        if param not in octopus_vars or octopus_vars[param] is None:
            octopus_vars[param] = val
    tdata = load_template(octopus_vars['web_site_name'], octopus_vars['environment_name'])
    octopus_vars['cr_cmdb_ci'] = tdata['Cmdb_Ci']
    octopus_vars['cr_implementation_plan'] = cleandoc(tdata['Install Plan'])
    octopus_vars['cr_test_plan'] = cleandoc(tdata['Testing Plan'])
    octopus_vars['cr_backout_plan'] = cleandoc(tdata['Rollback'])
    print('END: Setting deployment context')
    return octopus_vars


def run():
    """Script entry point runner method
    """
    octopus_vars = read_octopus_vars()
    cr_defaults = get_cr_defaults()
    context = set_context(octopus_vars, cr_defaults)
    api = ServiceNowApi(context)
    cr_number = api.create_change_request(context)
    printhighlight('CR number: %s' % cr_number)

    # Set cr_number for next steps
    set_octopusvariable('ServiceNow.Cr.Number', cr_number)

    # Move CR to implement state
    print('Graceful wait for 30 secs before moving CR to implement state')
    time.sleep(30)
    context['cr_state'] = 'implement'
    context['cr_number'] = cr_number
    is_implemented = api.update_change_request(context)
    if is_implemented:
        printhighlight('CR # %s is successfully moved to implement status' % cr_number)
    else:
        printwarning('Failed to move move CR # %s to implement status' % cr_number)
    

if __name__ == "<run_path>":
    run()
