function Execute(
    [Parameter(Mandatory = $false)][string] $WebSiteUrl,
    [Parameter(Mandatory = $false)][string] $SSLThumbprint = $null,
    [Parameter(Mandatory = $false)][string] $SSLCertificateLocation = "My",
    [Parameter(Mandatory = $false)][Int16] $Attempts = 5
) {
	$WebSiteUrl = $OctopusParameters["WebInstallServiceUrl"]
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    <#$SSLThumbprint = Get-ChildItem -Path Cert:\LocalMachine\$SSLCertificateLocation |
                     Where-Object {$_.Subject -match ".paypalcorp.com"} |
                     Select-Object -ExpandProperty Thumbprint#>
     $SSLThumbprint = "937548C0C8E2A7D8485EF518FAC6B6179B4F12DF"                

    $cert = Get-Childitem -Path cert:\localMachine\My\$SSLThumbprint

    Write-Output $cert

    $Version = $OctopusParameters["Octopus.Release.Number"]
    $EnvironmentName = $OctopusParameters["Octopus.Environment.Name"]
    $json = (@{ Version = $Version
    RelativePath = "$Version$EnvironmentName\pda.manifest"})| ConvertTo-Json

    $attemptCount = 0
    $operationIncomplete = $true
    $maxFailures = $Attempts
    $sleepBetweenFailures = 1
    
    Write-Output $json
    Write-Output $WebSiteUrl

    while ($operationIncomplete -and $attemptCount -lt $maxFailures) {
        $attemptCount = ($attemptCount + 1)
        if ($attemptCount -ge 2) {
            Write-Output "Waiting for $sleepBetweenFailures seconds before retrying..."
            Start-Sleep -s $sleepBetweenFailures
            Write-Output "Retrying..."
            $sleepBetweenFailures = ($sleepBetweenFailures * 2)
        }
        try {
            $response = Invoke-RestMethod -Uri $WebSiteUrl -Certificate $cert -Method Post -Body $json -ContentType application/json
            Write-Output $response
            if ($response -gt 0) {
                $VersionID = $response
                $get_response = Invoke-RestMethod -Uri "$WebSiteUrl/voc" -Certificate $cert -Method Get -ContentType application/json
                Write-Output $get_response
                if ($get_response -gt 0) {
                    $InstallVersionID2 = $get_response.InstallVersionID
                    write-output $InstallVersionID2
                    $put_json = (@{InstallVersionID = $InstallInstanceID }) | ConvertTo-Json
                    $put_response = Invoke-RestMethod -Uri "$WebSiteUrl/voc" -Certificate $cert -Method Put -Body $put_json -ContentType application/json
                    if ($put_response -gt 0) {
                        $operationIncomplete = $false
                    }
                }
            }
            else {
                Write-Warning "We cannot create the InstallVersion"
            }
        }
        catch [System.Exception] {
            if ($attemptCount -lt ($maxFailures)) {
                Write-Error ("Attempt $attemptCount of $maxFailures failed: " + $_.Exception.Message)
            }
            else {
                throw
            }
        }
    }
}
& Execute 
