# End-to-end smoke: register -> token -> /auth/me -> post -> search -> like -> recommend
# From project root:
#   .\scripts\smoke_api.ps1
#   .\scripts\smoke_api.ps1 -Base "http://127.0.0.1:8000"

param(
    [string]$Base = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch {}

$email = "smoke+$([guid]::NewGuid().ToString('n').Substring(0, 10))@example.com"
$pass = "Smokepass12"

Write-Host "== 1) POST /auth/register ==" -ForegroundColor Cyan
$regBody = @{ email = $email; password = $pass } | ConvertTo-Json
$reg = Invoke-RestMethod -Method Post -Uri "$Base/auth/register" -ContentType "application/json" -Body $regBody
Write-Host ("id={0} email={1}" -f $reg.id, $reg.email)

Write-Host "`n== 2) POST /auth/token ==" -ForegroundColor Cyan
$form = "username=$([uri]::EscapeDataString($email))&password=$([uri]::EscapeDataString($pass))"
$tokResp = Invoke-RestMethod -Method Post -Uri "$Base/auth/token" `
    -ContentType "application/x-www-form-urlencoded" -Body $form
$token = $tokResp.access_token
Write-Host ("token_type={0} (token len={1})" -f $tokResp.token_type, $token.Length)

$headers = @{ Authorization = "Bearer $token" }

Write-Host "`n== 3) GET /auth/me ==" -ForegroundColor Cyan
$me = Invoke-RestMethod -Headers $headers -Uri "$Base/auth/me"
Write-Host ($me | ConvertTo-Json -Compress)

Write-Host "`n== 4) POST /posts/ ==" -ForegroundColor Cyan
$postBody = @{
    content    = "Smoke test post from PowerShell"
    tags       = @("test")
    content_type = "text"
} | ConvertTo-Json
$post = Invoke-RestMethod -Method Post -Headers $headers -Uri "$Base/posts/" `
    -ContentType "application/json" -Body $postBody
Write-Host ("post id={0} author_id={1}" -f $post.id, $post.author_id)

Write-Host "`n== 5) GET /search/ (no JWT) ==" -ForegroundColor Cyan
$searchUrl = "$Base/search/?q=" + [uri]::EscapeDataString("squat") + "&limit=5&min_score=0"
$search = Invoke-RestMethod -Uri $searchUrl
Write-Host ("items count={0}" -f $search.items.Count)
$search.items | Select-Object -First 3 id, similarity, @{n='tags';e={$_.tags -join ','}} | Format-Table

Write-Host "`n== 5b) POST /posts/{id}/like (like first search hit for /recommend) ==" -ForegroundColor Cyan
if ($search.items.Count -gt 0) {
    $likeId = $search.items[0].id
    $null = Invoke-RestMethod -Method Post -Headers $headers -Uri "$Base/posts/$likeId/like"
    Write-Host ("Liked post_id=$likeId")
} else {
    Write-Host "No search results; skipping like (recommend may be empty)"
}

Write-Host "`n== 6) GET /recommend/ (requires JWT) ==" -ForegroundColor Cyan
$recUrl = "$Base/recommend/?limit=5&min_score=0"
$rec = Invoke-RestMethod -Headers $headers -Uri $recUrl
Write-Host ("items count={0}" -f $rec.items.Count)
$rec.items | Select-Object -First 3 id, similarity | Format-Table

Write-Host "`nDone. Test user: $email / $pass" -ForegroundColor Green
