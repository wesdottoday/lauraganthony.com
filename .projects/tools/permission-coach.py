#!/usr/bin/env python3
"""
Permission Coaching System for Project Template

This tool provides interactive guidance for setting up API tokens and permissions
required for the project template system. It helps users through the complete
setup process with validation and troubleshooting.

Usage:
    python permission-coach.py guide           # Interactive setup guidance
    python permission-coach.py validate        # Validate existing configuration
    python permission-coach.py troubleshoot    # Help resolve permission issues
    python permission-coach.py examples        # Show configuration examples
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PermissionCoach:
    """Interactive permission coaching system."""
    
    def __init__(self, project_root: str = None):
        """Initialize the permission coach.
        
        Args:
            project_root: Path to project root. If None, uses current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.projects_dir = self.project_root / ".projects"
        self.env_file = self.projects_dir / ".env"
        self.ssh_private_key = self.projects_dir / "maya_id_ed25519"
        self.ssh_public_key = self.projects_dir / "maya_id_ed25519.pub"
        
        # Service endpoints
        self.gitea_base_url = "https://git.y37.space"
        self.woodpecker_base_url = "https://ci.y37.space"
        self.authentik_base_url = "https://auth.y37.space"
        
        # Load current environment if available
        self.current_env = self._load_current_env()
    
    def _load_current_env(self) -> Dict[str, str]:
        """Load current environment variables if .env exists."""
        env_vars = {}
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            value = value.strip('"\'')
                            env_vars[key] = value
            except Exception:
                pass
        return env_vars
    
    def _print_header(self, title: str, char: str = "=") -> None:
        """Print a formatted header."""
        print(f"\n{char * 60}")
        print(f"{title}")
        print(f"{char * 60}")
    
    def _print_step(self, step_num: int, title: str) -> None:
        """Print a formatted step header."""
        print(f"\n📋 Step {step_num}: {title}")
        print("-" * 40)
    
    def _print_success(self, message: str) -> None:
        """Print a success message."""
        print(f"✅ {message}")
    
    def _print_warning(self, message: str) -> None:
        """Print a warning message."""
        print(f"⚠️  {message}")
    
    def _print_error(self, message: str) -> None:
        """Print an error message."""
        print(f"❌ {message}")
    
    def _print_info(self, message: str) -> None:
        """Print an info message."""
        print(f"💡 {message}")
    
    def _confirm_action(self, prompt: str) -> bool:
        """Ask user for confirmation."""
        response = input(f"{prompt} (y/n): ").strip().lower()
        return response in ['y', 'yes', 'true', '1']
    
    def _make_test_request(self, url: str, headers: Dict[str, str]) -> Tuple[bool, str]:
        """Make a test API request to validate permissions.
        
        Args:
            url: API endpoint URL
            headers: Request headers including auth
            
        Returns:
            Tuple of (success, message)
        """
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    return True, "API access successful"
                else:
                    return False, f"HTTP {response.status}"
        except urllib.error.HTTPError as e:
            error_msg = f"HTTP {e.code}"
            try:
                error_body = e.read().decode('utf-8')
                error_data = json.loads(error_body)
                if 'message' in error_data:
                    error_msg = f"HTTP {e.code}: {error_data['message']}"
            except:
                pass
            return False, error_msg
        except Exception as e:
            return False, str(e)
    
    def guide_gitea_setup(self) -> Optional[str]:
        """Guide user through Gitea API token setup."""
        self._print_step(1, "Gitea API Token Setup")
        
        print("Gitea API token is required for:")
        print("• Repository creation and management")
        print("• Issues and Pull Request management")
        print("• Collaboration and access control")
        print()
        
        # Check if user already has a token
        current_token = self.current_env.get("MAYA_GITEA_API_KEY")
        if current_token:
            print(f"Current token found: {current_token[:8]}...{current_token[-4:]}")
            if self._confirm_action("Use existing token?"):
                return current_token
        
        print("To create a new Gitea API token:")
        print(f"1. Open: {self.gitea_base_url}/user/settings/applications")
        print("2. Click 'Generate New Token'")
        print("3. Select the following scopes:")
        print("   ✓ repo (Full repository access)")
        print("   ✓ write:issue (Create and modify issues)")
        print("   ✓ write:pull_request (Create and modify pull requests)")
        print("   ✓ read:org (Read organization info)")
        print("4. Copy the generated token")
        print()
        
        if not self._confirm_action("Have you created the token?"):
            print("Please create the token first, then run this command again.")
            return None
        
        while True:
            token = input("Enter your Gitea API token: ").strip()
            if not token:
                print("Token cannot be empty. Please try again.")
                continue
            
            # Validate token
            print("🔍 Validating token...")
            headers = {"Authorization": f"token {token}"}
            success, message = self._make_test_request(f"{self.gitea_base_url}/api/v1/user", headers)
            
            if success:
                self._print_success("Gitea API token validated successfully!")
                return token
            else:
                self._print_error(f"Token validation failed: {message}")
                if not self._confirm_action("Try a different token?"):
                    return None
    
    def guide_woodpecker_setup(self) -> Optional[str]:
        """Guide user through Woodpecker CI token setup."""
        self._print_step(2, "Woodpecker CI Token Setup")
        
        print("Woodpecker CI token is required for:")
        print("• Automated build and deployment setup")
        print("• Repository CI/CD configuration")
        print("• Build monitoring and management")
        print()
        
        # Check if user already has a token
        current_token = self.current_env.get("MAYA_WOODPECKER_API_KEY")
        if current_token:
            print(f"Current token found: {current_token[:8]}...{current_token[-4:]}")
            if self._confirm_action("Use existing token?"):
                return current_token
        
        print("To create a new Woodpecker CI token:")
        print(f"1. Open: {self.woodpecker_base_url}")
        print("2. Login with your Gitea account")
        print("3. Go to User Settings (top right) → API Tokens")
        print("4. Click 'New Token'")
        print("5. Select permissions:")
        print("   ✓ repo (Repository access)")
        print("   ✓ admin (Administrative access)")
        print("6. Copy the generated token")
        print()
        
        if not self._confirm_action("Have you created the token?"):
            print("Please create the token first, then run this command again.")
            return None
        
        while True:
            token = input("Enter your Woodpecker CI token: ").strip()
            if not token:
                print("Token cannot be empty. Please try again.")
                continue
            
            # Validate token
            print("🔍 Validating token...")
            headers = {"Authorization": f"Bearer {token}"}
            success, message = self._make_test_request(f"{self.woodpecker_base_url}/api/user", headers)
            
            if success:
                self._print_success("Woodpecker CI token validated successfully!")
                return token
            else:
                self._print_error(f"Token validation failed: {message}")
                if not self._confirm_action("Try a different token?"):
                    return None
    
    def guide_ssh_setup(self) -> bool:
        """Guide user through SSH key setup."""
        self._print_step(3, "SSH Key Setup")
        
        print("SSH keys are required for:")
        print("• Automated git commits as 'maya' user")
        print("• Secure repository access")
        print("• CI/CD operations")
        print()
        
        # Check if SSH keys already exist
        if self.ssh_private_key.exists() and self.ssh_public_key.exists():
            print(f"SSH keys found:")
            print(f"• Private: {self.ssh_private_key}")
            print(f"• Public: {self.ssh_public_key}")
            
            if self._confirm_action("Use existing SSH keys?"):
                return self.validate_ssh_keys()
        
        print("Setting up new SSH keys...")
        
        # Generate SSH key pair
        key_comment = "maya@project-template"
        ssh_keygen_cmd = [
            "ssh-keygen",
            "-t", "ed25519",
            "-f", str(self.ssh_private_key),
            "-C", key_comment,
            "-N", ""  # No passphrase
        ]
        
        try:
            # Ensure .projects directory exists
            self.projects_dir.mkdir(exist_ok=True)
            
            print("🔑 Generating SSH key pair...")
            result = subprocess.run(ssh_keygen_cmd, capture_output=True, text=True, check=True)
            
            # Set correct permissions
            os.chmod(self.ssh_private_key, 0o600)
            os.chmod(self.ssh_public_key, 0o644)
            
            self._print_success("SSH key pair generated successfully!")
            
            # Show public key for user to add to Gitea
            with open(self.ssh_public_key, 'r') as f:
                public_key_content = f.read().strip()
            
            print()
            print("📋 Add this public key to your Gitea account:")
            print(f"1. Open: {self.gitea_base_url}/user/settings/keys")
            print("2. Click 'Add Key'")
            print("3. Paste the following public key:")
            print()
            print("─" * 60)
            print(public_key_content)
            print("─" * 60)
            print()
            
            if not self._confirm_action("Have you added the public key to Gitea?"):
                self._print_warning("SSH key was generated but not added to Gitea.")
                print("You can add it later by following the instructions above.")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self._print_error(f"Failed to generate SSH keys: {e}")
            return False
        except Exception as e:
            self._print_error(f"SSH key setup error: {e}")
            return False
    
    def validate_ssh_keys(self) -> bool:
        """Validate existing SSH keys."""
        if not self.ssh_private_key.exists():
            self._print_error(f"Private key not found: {self.ssh_private_key}")
            return False
        
        if not self.ssh_public_key.exists():
            self._print_error(f"Public key not found: {self.ssh_public_key}")
            return False
        
        # Check permissions
        private_stat = self.ssh_private_key.stat()
        if oct(private_stat.st_mode)[-3:] != '600':
            self._print_warning("Private key permissions should be 600")
            try:
                os.chmod(self.ssh_private_key, 0o600)
                self._print_success("Fixed private key permissions")
            except Exception as e:
                self._print_error(f"Could not fix permissions: {e}")
        
        # Validate key format
        try:
            with open(self.ssh_public_key, 'r') as f:
                public_key = f.read().strip()
            
            if not public_key.startswith('ssh-ed25519'):
                self._print_warning("Public key may not be in correct format")
                return False
            
            self._print_success("SSH keys validated successfully!")
            return True
            
        except Exception as e:
            self._print_error(f"Could not validate SSH keys: {e}")
            return False
    
    def create_env_file(self, gitea_token: str, woodpecker_token: str) -> bool:
        """Create .env file with tokens."""
        self._print_step(4, "Environment Configuration")
        
        env_content = f'''# Project Template Environment Configuration
# Generated by permission-coach.py

# Gitea API Token (for repository and issue management)
MAYA_GITEA_API_KEY={gitea_token}

# Woodpecker CI Token (for build automation)
MAYA_WOODPECKER_API_KEY={woodpecker_token}

# Additional configuration can be added here as needed
'''
        
        try:
            # Ensure .projects directory exists
            self.projects_dir.mkdir(exist_ok=True)
            
            with open(self.env_file, 'w') as f:
                f.write(env_content)
            
            # Set secure permissions
            os.chmod(self.env_file, 0o600)
            
            self._print_success(f"Environment file created: {self.env_file}")
            return True
            
        except Exception as e:
            self._print_error(f"Could not create environment file: {e}")
            return False
    
    def run_guided_setup(self) -> bool:
        """Run the complete guided setup process."""
        self._print_header("🚀 Permission Setup Wizard", "=")
        
        print("This wizard will guide you through setting up API tokens and")
        print("permissions required for the project template system.")
        print()
        print("You will need:")
        print("• Gitea account with repository access")
        print("• Woodpecker CI access (via Gitea login)")
        print("• Ability to add SSH keys to your Gitea account")
        print()
        
        if not self._confirm_action("Ready to begin setup?"):
            print("Setup cancelled.")
            return False
        
        # Step 1: Gitea API token
        gitea_token = self.guide_gitea_setup()
        if not gitea_token:
            self._print_error("Gitea token setup failed.")
            return False
        
        # Step 2: Woodpecker CI token
        woodpecker_token = self.guide_woodpecker_setup()
        if not woodpecker_token:
            self._print_error("Woodpecker token setup failed.")
            return False
        
        # Step 3: SSH keys
        if not self.guide_ssh_setup():
            self._print_error("SSH key setup failed.")
            return False
        
        # Step 4: Create .env file
        if not self.create_env_file(gitea_token, woodpecker_token):
            self._print_error("Environment file creation failed.")
            return False
        
        # Final validation
        self._print_header("🎉 Setup Complete!", "=")
        print("All permissions have been configured successfully!")
        print()
        print("Next steps:")
        print("• Run: python .projects/tools/permission-coach.py validate")
        print("• Initialize your project: python .projects/init_project.py")
        print("• Start creating issues: python .projects/tools/issue-mgr.py new")
        print()
        
        return True
    
    def validate_configuration(self) -> bool:
        """Validate all configuration and permissions."""
        self._print_header("🔍 Configuration Validation", "=")
        
        all_valid = True
        
        # Check .env file
        if not self.env_file.exists():
            self._print_error(f"Environment file not found: {self.env_file}")
            print("Run: python .projects/tools/permission-coach.py guide")
            return False
        
        self._print_success(f"Environment file found: {self.env_file}")
        
        # Load environment
        env_vars = self._load_current_env()
        
        # Validate Gitea token
        gitea_token = env_vars.get("MAYA_GITEA_API_KEY")
        if not gitea_token:
            self._print_error("MAYA_GITEA_API_KEY not found in .env file")
            all_valid = False
        else:
            print("🔍 Validating Gitea API token...")
            headers = {"Authorization": f"token {gitea_token}"}
            success, message = self._make_test_request(f"{self.gitea_base_url}/api/v1/user", headers)
            if success:
                self._print_success("Gitea API token is valid")
            else:
                self._print_error(f"Gitea API token validation failed: {message}")
                all_valid = False
        
        # Validate Woodpecker token
        woodpecker_token = env_vars.get("MAYA_WOODPECKER_API_KEY")
        if not woodpecker_token:
            self._print_error("MAYA_WOODPECKER_API_KEY not found in .env file")
            all_valid = False
        else:
            print("🔍 Validating Woodpecker CI token...")
            headers = {"Authorization": f"Bearer {woodpecker_token}"}
            success, message = self._make_test_request(f"{self.woodpecker_base_url}/api/user", headers)
            if success:
                self._print_success("Woodpecker CI token is valid")
            else:
                self._print_error(f"Woodpecker CI token validation failed: {message}")
                all_valid = False
        
        # Validate SSH keys
        if self.validate_ssh_keys():
            self._print_success("SSH keys are configured correctly")
        else:
            self._print_error("SSH key validation failed")
            all_valid = False
        
        # Summary
        if all_valid:
            self._print_header("✅ All Validations Passed!", "=")
            print("Your configuration is ready for project initialization!")
        else:
            self._print_header("❌ Validation Issues Found", "=")
            print("Please resolve the issues above before proceeding.")
            print("Run: python .projects/tools/permission-coach.py guide")
        
        return all_valid
    
    def troubleshoot_issues(self) -> None:
        """Provide troubleshooting guidance for common issues."""
        self._print_header("🔧 Troubleshooting Guide", "=")
        
        print("Common issues and solutions:")
        print()
        
        print("1. 'MAYA_GITEA_API_KEY not found'")
        print("   → Run: python .projects/tools/permission-coach.py guide")
        print("   → Ensure .env file exists in .projects/ directory")
        print()
        
        print("2. 'Gitea API token validation failed'")
        print(f"   → Check token at: {self.gitea_base_url}/user/settings/applications")
        print("   → Ensure token has 'repo', 'write:issue', 'write:pull_request' scopes")
        print("   → Token may have expired - create a new one")
        print()
        
        print("3. 'Woodpecker CI token validation failed'")
        print(f"   → Login to: {self.woodpecker_base_url}")
        print("   → Go to User Settings → API Tokens")
        print("   → Ensure token has 'repo' and 'admin' permissions")
        print()
        
        print("4. 'SSH key validation failed'")
        print("   → Check key files exist: maya_id_ed25519 and maya_id_ed25519.pub")
        print("   → Private key permissions should be 600")
        print("   → Add public key to Gitea: Settings → SSH/GPG Keys")
        print()
        
        print("5. 'Permission denied' during git operations")
        print("   → Ensure SSH key is added to your Gitea account")
        print("   → Test: ssh -T git@git.y37.space")
        print("   → Check git config: user.name, user.email, core.sshCommand")
        print()
        
        print("6. 'Repository creation failed'")
        print("   → Ensure you have organization access to 'y37.space'")
        print("   → Check Gitea token permissions")
        print("   → Repository name may already exist")
        print()
        
        # Interactive troubleshooting
        print("─" * 60)
        if self._confirm_action("Run diagnostic checks?"):
            self.validate_configuration()
    
    def show_examples(self) -> None:
        """Show configuration examples and templates."""
        self._print_header("📋 Configuration Examples", "=")
        
        print("Example .env file:")
        print("─" * 40)
        print("# Project Template Environment Configuration")
        print("MAYA_GITEA_API_KEY=gitea_abcdef1234567890")
        print("MAYA_WOODPECKER_API_KEY=wp_1234567890abcdef")
        print("─" * 40)
        print()
        
        print("Example SSH key generation:")
        print("─" * 40)
        print("ssh-keygen -t ed25519 -f .projects/maya_id_ed25519 -C 'maya@project-template'")
        print("─" * 40)
        print()
        
        print("Example git configuration:")
        print("─" * 40)
        print("git config user.name 'maya'")
        print("git config user.email 'maya@y37.space'")
        print("git config core.sshCommand 'ssh -i .projects/maya_id_ed25519'")
        print("─" * 40)
        print()
        
        print("Required API token scopes:")
        print("─" * 40)
        print("Gitea: repo, write:issue, write:pull_request, read:org")
        print("Woodpecker: repo, admin")
        print("─" * 40)
        print()
        
        print("Service URLs:")
        print("─" * 40)
        print(f"Gitea: {self.gitea_base_url}")
        print(f"Woodpecker CI: {self.woodpecker_base_url}")
        print(f"Authentik: {self.authentik_base_url}")
        print("─" * 40)


def main():
    """Main entry point for the permission coach tool."""
    parser = argparse.ArgumentParser(
        description="Permission coaching system for project template setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Complete guided setup
    python permission-coach.py guide
    
    # Validate existing configuration
    python permission-coach.py validate
    
    # Get help with issues
    python permission-coach.py troubleshoot
    
    # Show configuration examples
    python permission-coach.py examples
        """
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Guide command
    guide_parser = subparsers.add_parser("guide", help="Interactive setup guidance")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate configuration")
    
    # Troubleshoot command
    troubleshoot_parser = subparsers.add_parser("troubleshoot", help="Troubleshooting help")
    
    # Examples command
    examples_parser = subparsers.add_parser("examples", help="Show configuration examples")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize coach
    try:
        coach = PermissionCoach()
    except Exception as e:
        print(f"Error initializing permission coach: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == "guide":
            success = coach.run_guided_setup()
            sys.exit(0 if success else 1)
        
        elif args.command == "validate":
            success = coach.validate_configuration()
            sys.exit(0 if success else 1)
        
        elif args.command == "troubleshoot":
            coach.troubleshoot_issues()
        
        elif args.command == "examples":
            coach.show_examples()
    
    except KeyboardInterrupt:
        print("\n\n⛔ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()