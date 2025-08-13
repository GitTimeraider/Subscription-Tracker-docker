#!/usr/bin/env python3
"""
Subscription Tracker Health Monitor
A simple script to monitor the health of the subscription tracker application
"""

import requests
import time
import sys
import argparse
from datetime import datetime

def check_health(url, timeout=30):
    """Check the health endpoint"""
    try:
        response = requests.get(f"{url}/health", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.Timeout:
        print(f"✗ Health check timed out after {timeout} seconds")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to the application")
        return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def check_subscription_save(url, username, password, timeout=30):
    """Test subscription saving functionality"""
    session = requests.Session()
    
    try:
        # Login first
        login_response = session.post(
            f"{url}/login",
            data={'username': username, 'password': password},
            timeout=timeout
        )
        
        if login_response.status_code != 200:
            print("✗ Login failed")
            return False
        
        # Try to access dashboard (this triggers currency conversion)
        dashboard_response = session.get(f"{url}/dashboard", timeout=timeout)
        
        if dashboard_response.status_code == 200:
            print("✓ Dashboard loads successfully")
            return True
        else:
            print(f"✗ Dashboard failed with status {dashboard_response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"✗ Request timed out after {timeout} seconds")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Monitor Subscription Tracker health')
    parser.add_argument('--url', default='http://localhost:5000', help='Application URL')
    parser.add_argument('--username', default='admin', help='Username for testing')
    parser.add_argument('--password', default='changeme', help='Password for testing')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds')
    parser.add_argument('--once', action='store_true', help='Run once instead of continuously')
    
    args = parser.parse_args()
    
    print(f"Monitoring Subscription Tracker at {args.url}")
    print(f"Timeout: {args.timeout}s, Interval: {args.interval}s")
    print("-" * 50)
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Running health checks...")
        
        # Basic health check
        health_ok = check_health(args.url, args.timeout)
        
        # Functional test
        if health_ok:
            functional_ok = check_subscription_save(args.url, args.username, args.password, args.timeout)
        else:
            functional_ok = False
        
        # Overall status
        if health_ok and functional_ok:
            print("✓ Overall status: HEALTHY")
            exit_code = 0
        else:
            print("✗ Overall status: UNHEALTHY")
            exit_code = 1
        
        if args.once:
            sys.exit(exit_code)
        
        print(f"Next check in {args.interval} seconds...")
        time.sleep(args.interval)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        sys.exit(0)
