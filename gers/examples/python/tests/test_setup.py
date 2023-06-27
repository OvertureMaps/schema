import sys
import os

parent_dir = os.path.dirname(os.path.abspath(__file__))
#code_dir = os.path.join(os.path.dirname(parent_dir), "match-sidecar")
sys.path.insert(0, os.path.dirname(parent_dir))