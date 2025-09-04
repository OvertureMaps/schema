#!/usr/bin/env python3
"""
Simple validation test for the overture_gers_examples package.
This test verifies that the package can be imported and basic functionality works.
"""

import sys
import os

# Add the package to Python path for testing
sys.path.insert(0, os.path.dirname(__file__))

try:
    # Test basic imports
    from overture_gers_examples import __version__, TraceSnapOptions, MatchableFeature
    print(f"✓ Package imports successful - version {__version__}")
    
    # Test that key classes can be instantiated
    options = TraceSnapOptions()
    print("✓ TraceSnapOptions can be instantiated")
    
    # Test that the main function is accessible
    from overture_gers_examples import match_traces_main
    print("✓ Main function is accessible")
    
    print("\n🎉 All validation tests passed!")
    print("\nTo use this package:")
    print("1. Install in development mode: pip install -e .")
    print("2. Use the command line tool: match-traces --help")
    print("3. Import in Python: from overture_gers_examples import ...")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)