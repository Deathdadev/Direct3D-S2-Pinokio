module.exports = {
  run: [
    // Edit this step to customize the git repository to use
    {
      method: "shell.run",
      params: {
        message: [
          "git clone https://github.com/Deathdadev/Direct3D-S2.git app",
        ]
      }
    },
    // Add this step to copy setup-new.py to app/setup.py
    {
      method: "fs.copy",
      params: {
        src: "setup-new.py", // Source: setup-new.py in the current API folder
        dest: "app/setup.py"    // Destination: setup.py inside the cloned 'app' folder
      }
    },
    // Delete this step if your project does not use torch
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",                // Edit this to customize the venv folder path
          path: "app",                // Edit this to customize the path to start the shell from
          // xformers: true   // uncomment this line if your project requires xformers
          triton: true   // uncomment this line if your project requires triton
          // sageattention: true   // uncomment this line if your project requires sageattention
        }
      }
    },
    // Install Flash Attention for Windows/NVIDIA using prebuilt wheel (if available)
    // This step runs after PyTorch is installed.
    // It assumes find_flash_wheel.py and flash.txt are in the API project root.
    {
      method: "shell.run",
      params: {
        venv: "env", // Ensures the python from the venv is used
        path: "app", // Current working directory for the shell command
        // Conditional execution: only on Windows with an NVIDIA GPU
        when: "{{platform === 'win32' && kernel.gpu === 'nvidia' && kernel.gpus && kernel.gpus.length > 0}}",
        message: [
          // Execute the helper script.
          // '../find_flash_wheel.py' refers to the script in the API project root, relative to 'app'.
          // '../flash.txt' refers to flash.txt in the API project root.
          // The CUDA tag (cu128 or cu126) is determined based on GPU model, similar to torch.js logic.
          // Note: The `kernel.gpus.find(...)` logic for CUDA version needs to be robust.
          // The example ` / 50.+/.test(x.model)` is for 50-series. Adjust if your torch.js has more specific logic for cu126/cu128.
          `python ../find_flash_wheel.py {{kernel.gpus.find(x => / 50.+/.test(x.model)) ? 'cu128' : 'cu126'}} ../flash.txt`
        ]
      }
    },
    // Main dependency installation
    {
      method: "shell.run",
      params: {
        venv: "env",                // Edit this to customize the venv folder path
        path: "app",                // Edit this to customize the path to start the shell from
        build: true,
        env: {
          // "UV_DEFAULT_INDEX": "https://pypi.org/simple",
          // "UV_INDEX": "https://download.pytorch.org/whl/cu124",
          // "UV_FIND_LINKS": "https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.1_cu124.html",
          "UV_INDEX_STRATEGY": "unsafe-best-match",
          "UV_NO_BUILD_ISOLATION": 1,
          // "USE_NINJA": 0,
          "DISTUTILS_USE_SDK": 1
        },
        message: [
          "uv pip install -U setuptools",
          "uv pip install -r ../requirements-new.txt",
          "uv pip install -e .",
          "uv pip install gradio devicetorch timm kornia"
        ]
      }
    },
  ]
}
