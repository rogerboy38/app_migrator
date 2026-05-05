#!/usr/bin/env python3
"""Test if dependencies are properly declared"""

import configparser
import sys
import tomllib

print("🔍 Testing dependency declarations...")

# Test pyproject.toml
try:
    with open('pyproject.toml', 'rb') as f:
        data = tomllib.load(f)

    if 'project' in data and 'dependencies' in data['project']:
        deps = data['project']['dependencies']
        print(f"✅ pyproject.toml has {len(deps)} dependencies:")
        for dep in deps:
            print(f"   • {dep}")

        # Check for keyring
        if any('keyring' in dep for dep in deps):
            print("✅ keyring dependency declared")
        else:
            print("❌ keyring not in dependencies")
    else:
        print("❌ No dependencies in pyproject.toml")

except Exception as e:
    print(f"❌ Error reading pyproject.toml: {e}")

print("\n🔍 Testing setup.cfg...")
try:
    config = configparser.ConfigParser()
    config.read('setup.cfg')

    if 'options' in config and 'install_requires' in config['options']:
        requires = config['options']['install_requires']
        lines = [line.strip() for line in requires.split('\n') if line.strip()]
        print(f"✅ setup.cfg has {len(lines)} dependencies")

        if any('keyring' in line for line in lines):
            print("✅ keyring in install_requires")
        else:
            print("❌ keyring not in install_requires")
    else:
        print("❌ No install_requires in setup.cfg")

except Exception as e:
    print(f"❌ Error reading setup.cfg: {e}")

print("\n✅ Dependency declaration test complete")
