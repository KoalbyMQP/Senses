scriptpath = fileparts(mfilename('fullpath'));
addpath(scriptpath)
addpath('mr')
clc;
clear;

%% LEFT ARM
Slist = [[1;0;0;0; 8.68; 2.4], ...
        [0;0;1; -2.4; 425.8100; 0], ...
        [1;0;0; 0; -1.92; 2.4], ...
        [0;1;0;14.8500; 0; -269.0400], ...
        [1;0;0; 0; 0; 2]];
M = [[1, 0, 0, 451.04]; [0, 1, 0, 2.4]; [0, 0, 1, -8.68]; [0, 0, 0, 1]];
thetalist =[deg2rad(20); deg2rad(-90); deg2rad(0); deg2rad(-110); deg2rad(0)];


T = FKinBody(M, Slist, thetalist)

% Code to print matrix in Python or MATLAB syntax
fprintf("MATLAB: \n [")
for i = 1:3
    fprintf('%f, ', T(i,1:end-1)); % Print all elements except the last one
    fprintf('%f;\n', T(i,end))
end
fprintf('%f, ', T(4,1:end-1)); % Print all elements except the last one
fprintf('%f]\n \n', T(4,end))

fprintf("Python: \n")
fprintf('[[')
for i = 1:3
    fprintf('%f, ', T(i,1:(end-1)))
    fprintf('%f], \n [', T(i,end))
end
fprintf('%f, ', T(4,1:(end-1)))
fprintf('%f]] \n', T(4,end))