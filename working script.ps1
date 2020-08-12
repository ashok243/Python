#$website_url = "https://webappqa.paypalcorp.com/GenesysAA/api/Installs"
$version = "1.1.1.111140"
$description = "Test"
$environment = "QA"
$instance_name = "VOC"
$thumbprint = "937548C0C8E2A7D8485EF518FAC6B6179B4F12DF"

 

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$cert = Get-Childitem -Path cert:\localMachine\My\$thumbprint

 

$json = (@{ Version = $version
Description = $description 
RelativePath = "$version$environment\pda.manifest"})| ConvertTo-Json

 

$response = Invoke-RestMethod -Uri "https://webappqa.paypalcorp.com/GenesysAA/api/Installs" -Certificate $cert -Method Post -Body $json -ContentType application/json

write-output $response

if ($response -gt 0) {
               
$get_response = Invoke-RestMethod -Uri "https://webappqa.paypalcorp.com/GenesysAA/api/Installs/voc" -Certificate $cert -Method Get -ContentType application/json

write-output $get_response

$InstallVersionID2 = $get_response.InstallVerisonID

write-output $InstallVersionID2

}

if ($response -gt 0) {

$json = (@{InstallVersionID = $response }) | ConvertTo-Json

write-highlight $json
$response = Invoke-RestMethod -Uri "https://webappqa.paypalcorp.com/GenesysAA/api/Installs/voc" -Certificate $cert -Method Put -Body $json -ContentType application/json
}
else {
write-highlight "we cannot create the InstallVersion"
}


