module.exports = {
  run: [{
    method: "shell.run",
    params: {
      message: "git pull"
    }
  }, {
    method: "shell.run",
    params: {
      path: "app",
      message: [
        // Reset local changes in the 'app' directory to allow a clean pull.
        // This will discard the previously copied setup.py.
        "git reset --hard HEAD",
        "git pull"
      ]
    }
  }, {
    // After updating the repository, re-copy your custom setup-new.py
    // to app/setup.py to ensure it's used.
    method: "fs.copy",
    params: {
      from: "setup-new.py", // Assumes setup-new.py is in the same dir as update.js
      to: "app/setup.py"
    }
  }, {
    // Re-run installation steps that might depend on setup.py or updated requirements.
    // This is important if requirements.txt includes an editable install ('-e .')
    // or if the package itself needs to be re-installed with the custom setup.py.
    method: "shell.run",
    params: {
      venv: "env", // Venv path relative to the 'path' directory below
      path: "app", // Execute in the 'app' directory
      message: [
        "uv pip install -r requirements.txt"
        // You might also consider "uv pip install -e ." if you want to explicitly
        // re-install the package in editable mode using the new setup.py.
      ]
    }
  }]
}
