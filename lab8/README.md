# Lab08: Machine Learning - Abhigya Goel

## Question 1

Based on the U.S. Mint coin specifications:

- Green (~2.5g): Penny, specified at 2.500g
- Blue (~5.0g): Nickel, specified at 5.000g
- Orange (~5.7g): Quarter, specified at 5.670g

Coins of the same denomination vary in weight due to manufacturing tolerances, wear from circulation, and minor differences in metal composition across batches.

To classify a coin by weight, you set threshold ranges. For example, below ~3.5g is a penny, between ~3.5g and ~5.3g is a nickel, and above ~5.3g is a quarter. The thresholds go where the distributions overlap least.

## Question 2

The Light Sensor (analog) on the GrovePi Kit can measure reflected light intensity. By shining light on a coin and reading the reflected amount, larger or shinier coins produce higher readings, helping distinguish denominations.

## Question 3

- Dataset A: Linearly separable. A line can divide the two classes.
- Dataset B: Linearly separable. The classes occupy distinct regions.
- Dataset C: Not linearly separable. The classes are interleaved.
- Dataset D: Not linearly separable. The classes overlap spatially.
- Dataset E: Not linearly separable. One class surrounds the other in a circular pattern.
- Dataset F: Not linearly separable. The clusters can't be split by one line.

## Question 4

- (x-h)^2 + (y-k)^2 = r^2: Circle
- (ax+by+c)(Ax+By+C) = 0: Pair of straight lines
- (y-k)^2 = 4a(x-h): Parabola
- (x-h)^2/a^2 + (y-k)^2/b^2 = 1: Ellipse
- (x-h)(y-k) = c: Hyperbola

These curved or multi-line boundaries can separate data that a single straight line cannot.

## Question 5

Inputs: 2, 1, 2. Weights: 1, -2, 3. Bias: -2.

z = (2)(1) + (1)(-2) + (2)(3) + (-2) = 2 - 2 + 6 - 2 = 4

sigmoid(4) = 1 / (1 + e^(-4)) = 1 / 1.0183 = ~0.982

The neuron output is approximately 0.982.
