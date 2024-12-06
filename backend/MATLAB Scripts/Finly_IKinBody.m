scriptpath = fileparts(mfilename('fullpath'));
addpath(scriptpath)
addpath('mr')
clc;
clear;

deltaX = 0;
deltaY = 0;
deltaZ = 0;

%% LEFT ARM
Slist = [[1;0;0;0; 8.68; 2.4], ...
        [0;0;1; -2.4; 425.8100; 0], ...
        [1;0;0; 0; -1.92; 2.4], ...
        [0;1;0;14.8500; 0; -269.0400], ...
        [1;0;0; 0; 0; 2]];
M = [[1, 0, 0, 451.04]; [0, 1, 0, 2.4]; [0, 0, 1, -8.68]; [0, 0, 0, 1]];
T =  [-0.000000, 1.000000, -0.000000, 27.630000 + deltaX;
    -0.000000, 0.000000, 1.000000, -124.417878 + deltaY;
    1.000000, 0.000000, 0.000000, 193.310535 + deltaZ;
    0.000000, 0.000000, 0.000000, 1.000000];
thetalist0 =[deg2rad(20); deg2rad(-90); deg2rad(0); deg2rad(-110); deg2rad(0)];

eomg = 1;
ev = 0.01;
[thetalist, success] = IKinBody(Slist, M, T, thetalist0, eomg, ev);
success
thetalist = transpose(thetalist);

% Print the row vector separated by commas
fprintf("Radians: ")
fprintf('%f, ', thetalist(1:end-1)); % Print all elements except the last one
fprintf('%f\n', thetalist(end)); % Print the last element with a newline character

thetalist = rad2deg(thetalist);
fprintf("Degrees: ")
fprintf('%f, ', thetalist(1:end-1)); % Print all elements except the last one
fprintf('%f\n', thetalist(end)); % Print the last element with a newline character