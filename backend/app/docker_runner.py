import docker
import os

client = docker.from_env()

def run_in_docker(image, repo_url, steps, log_callback):
    commands = [f"git clone {repo_url} ."] + steps
    joined_cmd = " && ".join(commands)
    # Using sh to evaluate the combined command string
    sh_cmd = f"sh -c '{joined_cmd}'"

    log_callback(f"Starting container with image: {image}\n")
    log_callback(f"Running command: {sh_cmd}\n")

    container = client.containers.run(
        image=image,
        command=sh_cmd,
        detach=True,
        working_dir="/app"
    )
    
    for line in container.logs(stream=True):
        log_callback(line.decode('utf-8', errors='replace'))
        
    result = container.wait()
    exit_code = result["StatusCode"]
    container.remove()
    return exit_code
