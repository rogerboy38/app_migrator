def after_install():
    """Ensure app_migrator stays in apps.txt after installation"""
    import os
    bench_path = os.getenv('BENCH_PATH', '..')
    apps_file = os.path.join(bench_path, 'sites', 'apps.txt')
    
    if os.path.exists(apps_file):
        with open(apps_file, 'r') as f:
            apps = f.read().splitlines()
        
        if 'app_migrator' not in apps:
            with open(apps_file, 'a') as f:
                f.write('app_migrator\n')
            print("✅ Added app_migrator to apps.txt")
