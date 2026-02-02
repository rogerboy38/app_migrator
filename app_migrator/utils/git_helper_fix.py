import subprocess

def test_branch_status():
    """Test the branch status detection"""
    
    # Test manual commands
    print("Testing git commands manually:")
    
    # 1. Fetch upstream
    result = subprocess.run("git fetch upstream", shell=True, capture_output=True, text=True)
    print(f"Fetch upstream: {result.returncode}")
    
    # 2. Check if upstream/main exists
    result = subprocess.run("git show-ref refs/remotes/upstream/main", 
                          shell=True, capture_output=True, text=True)
    print(f"upstream/main exists: {result.returncode == 0}")
    if result.returncode == 0:
        print(f"upstream/main hash: {result.stdout.strip()}")
    
    # 3. Get local HEAD
    result = subprocess.run("git rev-parse HEAD", shell=True, capture_output=True, text=True)
    local_hash = result.stdout.strip()
    print(f"Local HEAD: {local_hash}")
    
    # 4. Try to get upstream/main hash
    result = subprocess.run("git rev-parse upstream/main 2>/dev/null || echo 'NOT_FOUND'", 
                          shell=True, capture_output=True, text=True)
    remote_hash = result.stdout.strip()
    print(f"upstream/main (rev-parse): {remote_hash}")
    
    # 5. Alternative: use git ls-remote
    result = subprocess.run("git ls-remote upstream main", shell=True, capture_output=True, text=True)
    print(f"ls-remote upstream main: {result.stdout.strip()}")

if __name__ == "__main__":
    test_branch_status()
