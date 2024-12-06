scriptpath = fileparts(mfilename('fullpath'));
addpath(scriptpath)
addpath('mr')
clc;
clear;

% UNITS ARE MM
deltaX = 0;
deltaY = 60;
deltaZ = 0;

%% LEFT LEG
% Slist = [[0;0;1; 468.7500; 22.6300; 0], ...
%         [0;-1;0; -25.6400; 0; -21.3700], ...
%         [1;0;0; 0; -29.1400; -450.4500], ...
%         [-1;0;0; 0; 29.1400; 266.5500], ...
%         [-1;0;0; 0; 29.1400; 35]];
% M = [[1, 0, 0, 22.63]; [0, 1, 0, -468.74]; [0, 0, 1, 12.74]; [0, 0, 0, 1]];
% T =  [1.000000, 0.000000, 0.000000, 22.630000 + deltaX;
% 0.000000, 0.939693, 0.342020, -445.572248 + deltaY;
% 0.000000, -0.342020, 0.939693, 85.850852 + deltaZ;
% 0.000000, 0.000000, 0.000000, 1.000000]
% thetalist0 =[deg2rad(0); deg2rad(0); deg2rad(-10); deg2rad(-20); deg2rad(10)];

%% RIGHT LEG 
Slist = [[0;0;1; 468.7500; -22.6300; 0], ...
        [0;-1;0; -25.6400; 0; 21.3700], ...
        [-1;0;0; 0; 29.1400; 450.4500], ...
        [1;0;0; 0; -29.1400; -266.5500], ...
        [1;0;0; 0; -29.1400; -35]];
M = [[1, 0, 0, -22.63]; [0, 1, 0, -468.74]; [0, 0, 1, 12.74]; [0, 0, 0, 1]];
T = [1.000000, 0.000000, 0.000000, -22.630000 + deltaX;
0.000000, 1, 0, -465.505182 + deltaY;
0.000000, 0, 1, 61.909442 + deltaZ;
0.000000, 0.000000, 0.000000, 1.000000]
thetalist0 =[deg2rad(0); deg2rad(0); deg2rad(20); deg2rad(40); deg2rad(-20)];

%% RIGHT ARM
% Slist = [[-1;0;0; 0; -37.5100; 8.7000], ...
%         [0;0;1; 8.7000; -318.5300; 0], ...
%         [-1;0;0; 0; -25.9100; 8.7000], ...
%         [0;1;0; -12.9800; 0; 161.7500], ...
%         [0;-1;0; 7; 0; -52]];
% M = [[1, 0, 0, -343.73]; [0, 1, 0, -8.7]; [0, 0, 1, -36.51]; [0, 0, 0, 1]];
% T =  [0.000000, 1.000000, 0.000000, -33.900000 + deltaX;
% -0.000000, 0.000000, -1.000000, 169.760000 + deltaY;
% -1.000000, 0.000000, 0.000000, 138.220000 + deltaZ;
% 0.000000, 0.000000, 0.000000, 1.000000];
% thetalist0 =[deg2rad(0); deg2rad(-90); deg2rad(0); deg2rad(90); deg2rad(0)];

%% LEFT ARM
% Slist = [[1;0;0;0; 37.51; -8.2], ...
%         [0;0;1; 8.2; 318.53; 0], ...
%         [-1;0;0; 0; -25.9100; 8.2], ...
%         [0;1;0;-12.9800; 0; -161.7500], ...
%         [0;-1;0; 7; 0; 52]];
% M = [[1, 0, 0, 343.73]; [0, 1, 0, -8.2]; [0, 0, 1, -36.51]; [0, 0, 0, 1]];
% T =   [0.000000, -1.000000, -0.000000, 33.400000 + deltaX;
% 0.000000, 0.000000, -1.000000, 169.760000 + deltaY;
% 1.000000, 0.000000, 0.000000, 138.220000 + deltaZ;
% 0.000000, 0.000000, 0.000000, 1.000000]
% thetalist0 =[deg2rad(0); deg2rad(90); deg2rad(0); deg2rad(-90); deg2rad(0)];

eomg = 0.01;
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