# cdmo_project
The repo contains the following folders:
- `source`: contains the source code organised in folders, one for each model type, as mentioned in the project description
- `res`: the other one mentioned in the assigment descripion: "Collect all the solutions under a res folder, by creating specific sub-folders (res/CP, res/SMT, res/MIP, etc.)".

### Run the docker container
Once cloned the repo follow the following steps:
0. Open a terminal inside the root folder (where the Dockerfile is placed)
2. Run `docker compose build` to build the container (only the first time)
3. Then, to start the container, run `docker compose up -d`.
4. Run `docker exec -it cdmo_solvers_container bash` to access a bash in the container
5. `docker-compose down` when finished  

## Running the models

### Run all models on all instances automatically
From inside a bash in the docker container run the command `python source/run_all.py`

### Run a CP model in the container
1. Open a terminal in the root folder of the project and run the container
2. Access to a bash inside it
3. `` where N is the instance number

### Run a CP model in the container  
1. Open a terminal in the root folder of the project and run the container  
2. Access a bash inside it  
3. Run the following command inside the container:  
   ```bash
   python source/CP/CP_STS.py -n <N> [--opt] [--heuristics] [--solver {chuffed,gecode,ortools}] [--no-symmetry-breaking]
   ```

   Where:
   - `<N>` is the number of teams (must be **even**)
   - `--opt`: run the optimization version (default: **disabled**)
   - `--heuristics`: use first-fail variable selection (default: **disabled**)
   - `--solver`: solver to use (default: **chuffed** for satisfaction, **ortools** for optimization)
   - `--no-symmetry-breaking`: disable symmetry breaking constraints (default: **enabled**)


### Run MIP model in the container
- **Run a single solver on the specified instance**:
    Once the container is running and you are inside a bash in it, run the command `python source/MIP/mip_model.py <N> <solver_index> [options]` to run the MIP model on instance N and the specified index of the solver. 
    Where the possible options are:
    - `-o`: the optimised version will be solved
    - `-cp`: canonical pairing will be applied
    - `-sb`: simmetry breaking constraint will be applied
    - `-cplex_br`: barrier algorithm will be used by CPLEX instead of symplex.
    
    Run `python source/MIP/mip_model.py -h` to see a help message listing all the available MIP models.

- **Run all MIP solvers on all instances**:
    Once the container is running and you're inside a bash in it, run the command `python source/MIP/mip_model.py -a` to automatically run all the solvers on all the instances.


### Check the solutions
To check if all the produced solutions are valid run the command: `python source/solution_checker.py res/<folder_name>` where `<folder_name>` is the name of the folder containing the jsons relative to the computed solutions (e.g. `res/MIP`).

### Additional notes
About MIP model, if you want to stop a solver before the time limit, open another terminal and run the command `pkill ampl` from inside the container.

