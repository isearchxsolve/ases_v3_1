import subprocess
import os
import shutil
from typing import Tuple

class SandboxExecutor:
    """
    Provides an isolated execution environment to physically test generated code.
    Prevents hallucinated passing of QA phases.
    """
    def __init__(self, project_dir: str):
        self.project_dir = project_dir

    def run_tests(self, test_cmd: str = "pytest -v") -> Tuple[bool, str]:
        """
        Executes a test command natively in the project directory.
        Returns a tuple of (success_boolean, output_string).
        """
        if not os.path.exists(self.project_dir):
            return False, f"Error: Project directory does not exist: {self.project_dir}"

        try:
            # We run the command locally in the project directory
            result = subprocess.run(
                test_cmd.split(),
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120 # 2 minute timeout
            )
            
            output = result.stdout
            if result.stderr:
                output += "\n--- STDERR ---\n" + result.stderr

            if result.returncode == 0:
                return True, output
            else:
                return False, output

        except subprocess.TimeoutExpired:
            return False, f"Error: Command '{test_cmd}' timed out after 120 seconds."
        except Exception as e:
            return False, f"Error executing command: {str(e)}"
