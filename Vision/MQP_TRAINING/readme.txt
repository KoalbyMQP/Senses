DOWNLOAD THIS FILE SEPERATELY TO YOUR COMPUTER BEFORE USING!!!!!!

Usage:
-----------PREP-----------
1.) download the SSH library for opencv (assuming you're using opencv)
2.) command+shift+P and type 'ssh', use the option that says 'Remote-SSH: Add new SSH host'
3.) type 'ssh <your wpi email name>@turing.wpi.edu
4.) press enter on the first option
5.) hit connect on the little pop-up
6.) type your turing account password
7.) you then want to open your turing account's SCRATCH folder
8.) pop this folder into the scratch folder & cd into it

-----------GET FILE READY-----------
1.) pop your downloaded dataset(s) into 'Datasets' folder
2.) in 'train.py' add a new 'train_yolo(...)' line, make sure model matches downloaded dataset model and file_path matches dataset name
3.) repeat for all models you want to train
4.) SAVE BEFORE RUNNING

-----------RUNNING-----------
1.) open terminal (cntrl+J) and type 'module load uv'
2.) type 'uv venv myenv', give it a second to load, then type the activation command it gives you
3.) type 'uv pip install ultralytics'
4.) type 'sinteractive', give it like 6 cpu cores, 1 gpu, leave gpu blank, and 16000 ram. Shouldn't need more than 30 mins and use short partition
5.) type 'python train.py' and run
6.) come back later, there should be a 'runs' folder that has your output files. Your model will be in 'weights' folder