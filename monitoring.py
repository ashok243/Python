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
        self.cr_get_url = params['url'] + "/number"
        self.authenticator = Authenticator(params).get_token()
        self.headers = {
            'Authorization': ' '.join([self.authenticator['token_type'], self.authenticator['access_token']]),
            'content-type': 'application/json'
        }


    def get_change_request(self, data):
        """Method for running patch requests on Change Request
        Args:
            data: dict() -> Change request data dictionary
        """
        print('BEGIN: Get change request')
        cr_response = None
        result = None
        cr_response = request_with_retry('GET', self.cr_get_url + "/" + data['cr_number'], headers=self.headers)
        print(cr_response)
        if cr_response and 'result' in cr_response:
            result = cr_response['result']
            
        print('END: Get change request')
        return result


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
                     'ServiceNow.Cr.Number']
    
    def return_if_var_exists(var):
        try:
            return get_octopusvariable(var)
        except Exception as e:
            failstep('Required variable "%s" is not set: %s' % (var, e))

    octopus_vars = {to_snake_case(var): return_if_var_exists(var) for var in required_vars}
    print('END: Reading octopus variables')
    return octopus_vars


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


def run():
    """Script entry point runner method
    """
    octopus_vars = read_octopus_vars()
    context = octopus_vars
    api = ServiceNowApi(context)
    cr_details = api.get_change_request(context)
    print(cr_details)
    

if __name__ == "<run_path>":
    run()
