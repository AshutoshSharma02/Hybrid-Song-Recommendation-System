<#
PowerShell helper to initialize Git LFS for this repository and move large files into LFS.
Run from the repository root in PowerShell:

    .\scripts\setup_git_lfs.ps1

This script will:
 - check for `git` and `git lfs`
 - run `git lfs install`
 - track common patterns (honors existing .gitattributes)
 - stage `.gitattributes`
 - optionally unstage previously committed large files (git rm --cached)
 - re-add files so they become LFS pointers
 - commit and push

Be careful: the optional `git lfs migrate` operation rewrites history and requires force-push.
#>

function Confirm($Message){
    $resp = Read-Host "$Message [y/N]"
    return $resp -match '^[Yy]'
}

Write-Host "== Git LFS setup helper ==" -ForegroundColor Cyan

# Check git
try{
    git --version | Out-Null
}catch{
    Write-Error "git not found. Install git first and re-run this script."
    exit 1
}

# Check git-lfs
$hasLfs = $false
try{
    git lfs version > $null 2>&1
    $hasLfs = $true
}catch{
    $hasLfs = $false
}

if (-not $hasLfs){
    Write-Warning "git-lfs not detected. Please install Git LFS from https://git-lfs.github.com and re-run this script."
    if (-not (Confirm "Continue anyway (skip LFS commands)?")) { exit 1 }
}

# Initialize LFS
Write-Host "Running: git lfs install" -ForegroundColor Yellow
git lfs install

# Track patterns (will append to .gitattributes if not present)
$patterns = @(
    'data/*.npz',
    'data/*.npy',
    'data/*.joblib',
    'data/*.csv',
    'transformer.joblib'
)

foreach ($p in $patterns){
    Write-Host "Tracking: $p" -ForegroundColor DarkGray
    git lfs track "$p" 2>$null
}

# Stage .gitattributes
if (Test-Path .gitattributes){
    git add .gitattributes
}

# Optionally unstage previously committed large files so LFS will track them
if (Confirm "Unstage cached data files (git rm --cached -r data)? This modifies the index but not working tree."){
    try{
        git rm --cached -r data 2>$null
        git rm --cached transformer.joblib 2>$null
    }catch{
        Write-Warning "Some files weren't present in the index or could not be removed; continuing."
    }
}

# Re-add files so LFS pointers are created
Write-Host "Re-adding files to index (this will create LFS pointers for tracked patterns)" -ForegroundColor Yellow
git add data transformer.joblib 2>$null || Write-Host "No matching files to add or already staged."

# Commit changes
$commitMessage = "Move large data files to Git LFS"
try{
    git commit -m "$commitMessage"
}catch{
    Write-Host "Nothing to commit (maybe files already tracked by LFS or no changes)." -ForegroundColor Green
}

# Push to remote
if (Confirm "Push to remote 'origin' branch 'main' now?"){
    Write-Host "Pushing to origin main (this also uploads LFS objects)" -ForegroundColor Yellow
    git push origin main
}else{
    Write-Host "Skipping push. You can push manually later: git push origin main" -ForegroundColor Cyan
}

# Show LFS-tracked files
Write-Host "Currently tracked LFS files:" -ForegroundColor Cyan
try{
    git lfs ls-files
}catch{
    Write-Host "git lfs ls-files failed or git-lfs not installed." -ForegroundColor Yellow
}

# Offer migrate option (rewrites history)
if (Confirm "Do you need to rewrite history to migrate existing commits into LFS? (advanced, rewrites history)"){
    Write-Warning "This operation rewrites git history. All collaborators must re-clone or coordinate."
    if (Confirm "Proceed with `git lfs migrate import --include=...` and force-push?" ){
        $include = 'data/*.npz,data/*.npy,data/*.joblib,data/*.csv,transformer.joblib'
        Write-Host "Running: git lfs migrate import --include=$include" -ForegroundColor Yellow
        git lfs migrate import --include=$include
        Write-Host "Force pushing rewritten history to origin/main" -ForegroundColor Yellow
        git push --force origin main
    }else{
        Write-Host "Skipping migrate." -ForegroundColor Cyan
    }
}

Write-Host "Done." -ForegroundColor Green
