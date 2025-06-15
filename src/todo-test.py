import gradio as gr
import requests
import yaml
import asyncio
import httpx
import json

class SmartTodoApp:
    def __init__(self):
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

        self.api_key = config["api_key"]
        self.base_url = config["model_server_base_url"]
        self.stream = config["stream"]
        self.stream_timeout = config["stream_timeout"]
        self.workspace_slug = config["workspace_slug"]

        if self.stream:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/stream-chat"
        else:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/chat"

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key
        }
       
        # Store tasks
        self.tasks = []

    def get_suggestions(self, task: str) -> list:
        """
        Get task suggestions based on the input task using the LLM API.
        """
        import re
        import json
        
        # Create a more explicit prompt for the LLM
        prompt = f"""
        Need 3 specific and practical follow-up tasks related to this task: '{task}'.
        Format your response as a simple list of 3 suggestions which follow-up to the task in 1 phrase (short) like to-do list.
        For example:
        1. First follow-up related to the task
        2. Second follow-up related to the task
        3. Third follow-up related to the task
        """
        
        data = {
            "message": prompt,
            "mode": "chat",
            "sessionId": "todo-session-id",
            "attachments": []
        }
        
        try:
            # Print debug info
            print(f"Sending request to: {self.chat_url}")
            print(f"Headers: {self.headers}")
            print(f"Data: {data}")
            
            # Make the API request
            response = requests.post(
                self.chat_url,
                headers=self.headers,
                json=data,
                timeout=15,
                stream=True  # Enable streaming for SSE
            )
            
            # Print response status and headers for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            
            # Check if response is successful
            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(f"Response content: {response.text}")
                return ["Check API connection", "Make sure the model is running", "Verify API key"]
            
            # For SSE responses, we need to collect the chunks and reconstruct the text
            collected_text = ""
            sse_data = ""
            
            try:
                # Read the streaming response and collect all text chunks
                for line in response.iter_lines():
                    if line:
                        # Decode the line
                        line = line.decode('utf-8')
                        sse_data += line + "\n"
                        
                        # Check if this is an SSE data line
                        if line.startswith('data: '):
                            data_str = line[6:]  # Remove 'data: ' prefix
                            try:
                                data_json = json.loads(data_str)
                                if 'textResponse' in data_json:
                                    collected_text += data_json['textResponse']
                            except json.JSONDecodeError:
                                continue
                
                print(f"Collected full text: {collected_text}")
                
                # Now parse the complete text
                suggestions = []
                
                # Look for numbered items (1. item, 2. item, etc.)
                numbered_pattern = re.compile(r'(?:^|\n)\s*(\d+)[\.\)]\s*(.+?)(?=\n\s*\d+[\.\)]|$)', re.DOTALL)
                matches = numbered_pattern.findall(collected_text)
                
                if matches:
                    # Sort by number to ensure correct order
                    sorted_matches = sorted(matches, key=lambda x: int(x[0]))
                    suggestions = [match[1].strip() for match in sorted_matches]
                    return suggestions[:3]
                
                # If no numbered list, try to split by lines
                if not suggestions:
                    lines = [line.strip() for line in collected_text.split('\n') if line.strip()]
                    for line in lines:
                        # Try to identify if line starts with a number
                        if re.match(r'^\d+[\.\)]\s+', line):
                            suggestion = re.sub(r'^\d+[\.\)]\s+', '', line).strip()
                            suggestions.append(suggestion)
                            
                    if suggestions:
                        return suggestions[:3]
                
                # If still no suggestions, split by sentences
                if not suggestions:
                    sentences = re.split(r'[.!?]+', collected_text)
                    meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
                    if meaningful_sentences:
                        return meaningful_sentences[:3]
                
                # Last resort: just return the whole text in chunks
                if not suggestions:
                    if collected_text:
                        return [collected_text]
                    else:
                        return ["Could not parse response", "Try different task description", "Check API documentation"]
                    
            except Exception as e:
                print(f"Error processing streaming response: {e}")
                print(f"Raw SSE data received: {sse_data}")
                return ["Error processing streaming response", "Check logs for details", "Try again later"]
                    
        except requests.exceptions.RequestException as e:
            print(f"Request exception: {e}")
            return ["Connection error", "Check network connection", "Verify API endpoint"]
        except Exception as e:
            print(f"Unexpected error in get_suggestions: {e}")
            return ["Unexpected error", "Check logs for details", "Try again later"]



    def add_task(self, task: str):
        """
        Add a task to the to-do list.
        """
        if task and task not in self.tasks:
            self.tasks.append(task)
        return self.tasks

    def remove_task(self, task_index: int):
        """
        Remove a task from the to-do list.
        """
        if 0 <= task_index < len(self.tasks):
            self.tasks.pop(task_index)
        return self.tasks

def main():
    todo_app = SmartTodoApp()

    with gr.Blocks() as app:
        gr.Markdown("# Smart To-Do App")
       
        with gr.Row():
            with gr.Column(scale=3):
                task_input = gr.Textbox(label="Add a task", placeholder="Enter a new task...")
                add_task_button = gr.Button("Add Task", variant="primary")
           
            with gr.Column(scale=2):
                suggestions_list = gr.Dataframe(
                    headers=["Suggestions"],
                    datatype=["str"],
                    row_count=3,
                    col_count=1,
                    interactive=False
                )

        tasks_list = gr.Dataframe(
            headers=["Tasks"],
            datatype=["str"],
            row_count=(5, "dynamic"),
            col_count=1,
            interactive=False
        )
       
        remove_button = gr.Button("Remove Selected Task")
        selected_task_index = gr.Number(value=-1, visible=False)
       
        # Get suggestions for a task
        def on_get_suggestions(task):
            if not task.strip():
                return [[""]]
           
            suggestions = todo_app.get_suggestions(task)
            return [[s] for s in suggestions]
       
        # Add a task and get suggestions
        def on_add_task(task):
            if not task.strip():
                return "", [], [[""]]
           
            # Add the task
            todo_app.add_task(task)
            
            # Get suggestions for the task
            suggestions = todo_app.get_suggestions(task)
            
            # Clear the input field, update tasks list, and show suggestions
            return "", todo_app.tasks, [[s] for s in suggestions]
       
        # Add a task from suggestions
        def on_suggestion_select(evt: gr.SelectData, suggestions):
            if evt.index[0] < len(suggestions) and suggestions[evt.index[0]][0]:
                selected_suggestion = suggestions[evt.index[0]][0]
                todo_app.add_task(selected_suggestion)
                
                # Get new suggestions for the selected task
                new_suggestions = todo_app.get_suggestions(selected_suggestion)
                
                return todo_app.tasks, [[s] for s in new_suggestions]
            return todo_app.tasks, [[""]]
       
        # Set selected task index
        def on_task_select(evt: gr.SelectData):
            selected_task = todo_app.tasks[evt.index[0]]
            
            # Get suggestions for the selected task
            suggestions = todo_app.get_suggestions(selected_task)
            
            return evt.index[0], [[s] for s in suggestions]
       
        # Remove selected task
        def on_remove_button(index):
            return todo_app.remove_task(index), -1
       
        # Connect events
        add_task_button.click(
            on_add_task,
            inputs=[task_input],
            outputs=[task_input, tasks_list, suggestions_list]
        )
       
        suggestions_list.select(
            on_suggestion_select,
            inputs=[suggestions_list],
            outputs=[tasks_list, suggestions_list]
        )
       
        # Disable the enter key submission
        # task_input.submit(
        #     on_task_input_submit,
        #     inputs=[task_input],
        #     outputs=[task_input, tasks_list]
        # )
       
        tasks_list.select(
            on_task_select,
            outputs=[selected_task_index, suggestions_list]
        )
       
        remove_button.click(
            on_remove_button,
            inputs=[selected_task_index],
            outputs=[tasks_list, selected_task_index]
        )

    app.launch()

if __name__ == "__main__":
    main()