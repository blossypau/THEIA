"""Explicit public-demo settings; local desktop behavior remains the default."""
import os


def public_demo():return os.environ.get('THEIA_PUBLIC_DEMO')=='1'


def internal_origin():
    return 'http://127.0.0.1:'+str(int(os.environ.get('PORT','8540')))
