scriptpath = fileparts(mfilename('fullpath'));
addpath(scriptpath)
addpath('mr')

wpts = [
    0 0 0 0 0;
    0 0 0 0 0;
    -0.349066 -0.337710 -0.636551 -0.936060 -0.349066;
    -0.349066 -0.415672 -1.286623 -1.312802 -0.349066;
    0.349066 0.427027 0.650072 0.725808 0.349066
];
tpts = [0, 3, 4, 5, 6];
tvec = 0:0.01:10;
[q, qd, qdd, pp] = quinticpolytraj(wpts, tpts, tvec);

Slist = [[0;0;1; 468.7500; 22.6300; 0], ...
        [0;-1;0; -25.6400; 0; -21.3700], ...
        [1;0;0; 0; -29.1400; -450.4500], ...
        [1;0;0; 0; -29.1400; -266.5500], ...
        [-1;0;0; 0; 29.1400; 35]];
M = [[1, 0, 0, 22.63]; [0, 1, 0, -468.74]; [0, 0, 1, 12.74]; [0, 0, 0, 1]];

[rows, col] = size(q);
p=[];
for i = 1:col
    thetas = q(:, i);
    thetalist =[thetas(1); thetas(2); thetas(3); thetas(4); thetas(5)];
    T = FKinBody(M, Slist, thetalist);
    new_p = [T(1,4); T(2,4); T(3,4)];
    p = [p new_p];
end

% figure;
% plot(tvec, p)

figure;
plot(tvec, q)
hold all
plot(tpts, wpts(1,:), 'x')
plot(tpts, wpts(2,:), 'x')
plot(tpts, wpts(3,:), 'x')
plot(tpts, wpts(4,:), 'x')
plot(tpts, wpts(5,:), 'x')
xlabel('t')
ylabel('Angles')
% legend('X-positions','Y-positions')
hold off
