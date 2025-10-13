def before_migrate():
    """Ensure app_migrator is in apps.txt before migration"""
    import os
    bench_path = os.getenv('BENCH_PATH', '..')
    apps_file = os.path.join(bench_path, 'sites', 'apps.txt')
    
    # Read current apps
    if os.path.exists(apps_file):
        with open(apps_file, 'r') as f:
            apps = set(f.read().splitlines())
    else:
        apps = set()
    
    # Add app_migrator if missing
    if 'app_migrator' not in apps:
        apps.add('app_migrator')
        with open(apps_file, 'w') as f:
            f.write('\n'.join(sorted(apps)) + '\n')
