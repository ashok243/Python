#$website_url = "https://webappqa.paypalcorp.com/GenesysAA/api/Installs"
$version = $OctopusParameters["Octopus.Release.Number"]
$description = "TEST"
$environment = $OctopusParameters["Octopus.Environment.Name"]
$instance_name = $OctopusParameters["InstanceName"]
$thumbprint = "937548C0C8E2A7D8485EF518FAC6B6179B4F12DF"

$webservice_url = $OctopusParameters["WebInstallServiceUrl"]

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$cert = Get-Childitem -Path cert:\localMachine\My\$thumbprint

$json = (@{ Version = $version
Description = $description 
RelativePath = "$version$environment\pda.manifest"})| ConvertTo-Json

$response = Invoke-RestMethod -Uri $webservice_url -Certificate $cert -Method Post -Body $json -ContentType application/json

write-output $response

if ($response -gt 0) {
    $get_response = Invoke-RestMethod -Uri $webservice_url/$instance_name -Certificate $cert -Method Get -ContentType application/json

    write-output $get_response
    $InstallVersionID2 = $get_response.InstallVerisonID
    write-output $InstallVersionID2
}

if ($response -gt 0) {
    $json = (@{InstallVersionID = $response }) | ConvertTo-Json
    write-highlight $json
    $response = Invoke-RestMethod -Uri $webservice_url/$instance_name -Certificate $cert -Method Put -Body $json -ContentType application/json
    write-output $response
}
else {
    write-highlight "we cannot create the InstallVersion"
}


