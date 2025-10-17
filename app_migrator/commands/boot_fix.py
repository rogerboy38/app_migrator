#!/usr/bin/env python3
"""
Boot Fix Command for App Migrator
"""

import click
from pathlib import Path
import sys

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ultimate_boot_fixer import UltimateBootFixer

@click.command()
@click.option('--bench-path', default='.', help='Path to bench directory')
@click.option('--test-only', is_flag=True, help='Test only, do not apply fixes')
@click.option('--nuclear', is_flag=True, help='Apply comprehensive nuclear fixes')
def boot_fix(bench_path, test_only, nuclear):
    """Fix Frappe boot issues that prevent app migration"""
    
    bench_path = Path(bench_path).absolute()
    
    if not (bench_path / "apps" / "frappe").exists():
        click.echo("❌ Not a valid Frappe bench directory")
        return
    
    if test_only:
        fixer = UltimateBootFixer(bench_path)
        success = fixer.test_boot_fix()
        if success:
            click.echo("✅ Boot test passed - no issues found")
        else:
            click.echo("❌ Boot test failed - run without --test-only to fix")
    else:
        if nuclear:
            click.echo("🚀 Applying NUCLEAR boot fixes...")
            fixer = UltimateBootFixer(bench_path)
            fixes = fixer.nuclear_fix()
        else:
            click.echo("🔧 Applying standard boot fixes...")
            from core.boot_fixer import BootFixer
            fixer = BootFixer(bench_path)
            fixes = fixer.fix_boot_issues()
        
        if fixes:
            click.echo(f"✅ Applied {len(fixes)} fixes:")
            for fix in fixes:
                click.echo(f"   - {fix}")
        else:
            click.echo("✅ No fixes needed")
        
        # Test the fix
        click.echo("\n🧪 Testing boot fix...")
        success = fixer.test_boot_fix()
        
        if success:
            click.echo("🎉 Boot issues resolved!")
        else:
            click.echo("⚠️  Some issues may remain")

if __name__ == "__main__":
    boot_fix()
