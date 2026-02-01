import click
import sys
import os

# Try to import the git_push command directly
sys.path.insert(0, '.')

try:
    from app_migrator.commands.git_push import git_push
    print(f"✅ git_push imported successfully")
    print(f"Command name: {git_push.name}")
    print(f"Command callback: {git_push.callback}")
    
    # Try to create a test CLI
    @click.group()
    def cli():
        pass
    
    cli.add_command(git_push, 'git-push')
    print(f"\n✅ Command added to CLI group")
    
    # Test help
    print(f"\n🔍 Testing help output:")
    try:
        from click.testing import CliRunner
        runner = CliRunner()
        result = runner.invoke(cli, ['git-push', '--help'])
        print(f"Exit code: {result.exit_code}")
        print(f"Output:\n{result.output[:200]}...")
    except Exception as e:
        print(f"❌ Help test failed: {e}")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
