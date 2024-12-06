
%% THIS IS A WORK IN PROGRESS, DO NOT RELY

scriptpath = fileparts(mfilename('fullpath'));
addpath(scriptpath)
addpath('mr')
clc;
clear;

deltaX = 0;
deltaY = 30;
deltaZ = 75;

%% RIGHT ARM
Slist = [[-1;0;0; 0; -37.5100; 8.7000], ...
        [0;0;1; 8.7000; -318.5300; 0], ...
        [1;0;0; 0; 25.9100; -8.7000], ...
        [0;1;0; -12.9800; 0; 161.7500], ...
        [0;-1;0; 7; 0; -52]];
M = [[1, 0, 0, -343.73]; [0, 1, 0, -8.7]; [0, 0, 1, -36.51]; [0, 0, 0, 1]];
T =  [1.000000, -0.000000, 0.000000, -16.500000 + deltaX;
       0.000000, 1.000000, 0.000000, -151.915255 + deltaY;
      -0.000000, 0.000000, 1.000000, 86.077422 + deltaZ;
       0.000000, 0.000000, 0.000000, 1.000000];
thetalist0 = [deg2rad(-20); deg2rad(90); deg2rad(0); deg2rad(110); deg2rad(0)];

%% LEFT LEG
% Slist = [[0;0;1; 468.7500; 22.6300; 0], ...
%         [0;-1;0; -25.6400; 0; -21.3700], ...
%         [1;0;0; 0; -29.1400; -450.4500], ...
%         [1;0;0; 0; -29.1400; -266.5500], ...
%         [-1;0;0; 0; 29.1400; 35]];
% 
% % Step One: Inverse Kinematics
% M = [[1, 0, 0, 22.63]; [0, 1, 0, -468.74]; [0, 0, 1, 12.74]; [0, 0, 0, 1]];
% T = [1.000000, 0.000000, 0.000000, 22.630000 + deltaX;
%     0.000000, 1.000000, 0.000000, -443.685299 + deltaY;
%     0.000000, 0.000000, 1.000000, -3.557260 + deltaZ;
%     0.000000, 0.000000, 0.000000, 1.000000];
% thetalist0 =[deg2rad(0); deg2rad(0); deg2rad(-20); deg2rad(40); deg2rad(20)];

eomg = 1;
ev = 0.01;
[thetalist, success] = IKinBody(Slist, M, T, thetalist0, eomg, ev);
J = JacobianBody(Slist, thetalist)

Vd = [1; 0; 0; 0; 0; 0]; % Desired end-effector velocity
qDot = pinv(J) * Vd;

% Print the row vector separated by commas
fprintf('%f, ', qDot(1:end-1)); % Print all elements except the last one
fprintf('%f\n', qDot(end)); % Print the last element with a newline character
