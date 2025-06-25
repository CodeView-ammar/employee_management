#!/usr/bin/env python
"""Main entry point for the Django application."""
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "employee_management.settings")
    
    from django.core.management import execute_from_command_line
    
    # Default to running the development server
    if len(sys.argv) == 1:
        sys.argv.append("runserver")
        sys.argv.append("0.0.0.0:5000")
    
    execute_from_command_line(sys.argv)