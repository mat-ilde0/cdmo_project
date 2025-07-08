# Base image
FROM minizinc/minizinc:latest

# Install system packages
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \            
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3 /usr/bin/python

# Set environment variable to allow breaking system packages
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Install Python packages
COPY requirements.txt /app/requirements.txt
RUN pip install --break-system-packages -r /app/requirements.txt

# Install AMPL solvers separately to avoid conflicts
RUN python3 -m amplpy.modules install highs
RUN python3 -m amplpy.modules install gurobi  
RUN python3 -m amplpy.modules install cplex

# Set working directory
WORKDIR /cdmo

# Copy application files
ADD . .

RUN chmod +x source/run_all.sh

# Default command
CMD ["/bin/bash"]