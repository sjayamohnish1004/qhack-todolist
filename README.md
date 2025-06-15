# SMART TO-DO LIST WITH AI SUGGESTIONS

A to-do list which runs on local/edge to provide real-time suggestions to the tasks given by the user. User can get a list of tasks which help in completing the task aforementioned. Uses AnythingLLM with access to NPU from Snapdragon X Elite and runs on top of Llama 3.2 3B Chat 8K.

### Hardware
- Machine: Lenovo ThinkPad
- Chip: Snapdragon X Elite
- OS: Windows 11
- Memory: 32 GB

### Software
- Python Version: 3.13.5
- AnythingLLM LLM Provider: Qualcomm QNN
- AnythingLLM Chat Model: Llama 3.2 3B Chat 8K

### Setup
1. Install and setup ARM based [AnythingLLM](https://anythingllm.com/).
    1. Choose Qualcomm QNN when prompted to choose an LLM provider to target the NPU
    2. Choose a model of your choice when prompted. This sample uses Llama 3.2 3B Chat with 8K context
2. Create a workspace by clicking "+ New Workspace"
3. Generate an API key
    1. Click the settings button on the bottom of the left panel
    2. Open the "Tools" dropdown
    3. Click "Developer API"
    4. Click "Generate New API Key"
4. Open a PowerShell instance and clone the repo
    ```
    git clone https://github.com/sjayamohnish1004/qhack-todolist.git
    ```
5. Create and activate your virtual environment with reqs
    ```
    # 1. navigate to the cloned directory
    cd qhack-todolist

    # 2. create the python virtual environment
    python -m venv venv

    # 3. activate the virtual environment
    ./venv/Scripts/activate     # windows

    # 4. install the requirements
    pip install -r requirements.txt
    ```
6. Create your `config.yaml` file with the following variables
    ```
    api_key: "your-key-here"
    model_server_base_url: "http://localhost:3001/api/v1"
    workspace_slug: "your-slug-here"
    stream: true
    stream_timeout: 60

### Usage
Go to src directory to access the main python file and run it from there:

    cd src
    python todo-test.py