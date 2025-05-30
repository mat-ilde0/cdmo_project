# Base image
FROM ubuntu:22.04

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (minizinc via pip = portabile)
COPY requirements.txt /app/requirements.txt
RUN python3 -m pip install --upgrade pip && \
    pip install --break-system-packages -r /app/requirements.txt && \
    python -m amplpy.modules install highs gurobi cbc gcg

# Set working directory
WORKDIR /cdmo

# TODO-copy volumes before delivering the project
ADD . .

# Ensure run scripts are executable
#RUN chmod +x run_model.sh run_all.sh
COPY run_solver_in_container.sh /app/run_solver_in_container.sh
RUN chmod +x /app/run_solver_in_container.sh

# Default command
CMD ["/bin/bash"]
