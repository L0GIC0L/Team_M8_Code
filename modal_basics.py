import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

# Sample data (replace with your actual data)
time = np.linspace(0, 1, 1000)
input_force = np.sin(2 * np.pi * 50 * time)  # Example input force
output_acceleration = np.sin(2 * np.pi * 50 * time) + 0.5 * np.sin(2 * np.pi * 120 * time)  # Example output acceleration

# Perform FFT
input_fft = fft(input_force)
output_fft = fft(output_acceleration)
frequencies = fftfreq(len(time), time[1] - time[0])

# Only keep the positive frequencies
positive_frequencies = frequencies[:len(frequencies)//2]
input_fft = input_fft[:len(input_fft)//2]
output_fft = output_fft[:len(output_fft)//2]

# Calculate the FRF
frf = output_fft / input_fft

# Plot the FRF
plt.figure()
plt.plot(positive_frequencies, np.abs(frf))
plt.xlabel('Frequency (Hz)')
plt.ylabel('FRF Magnitude')
plt.title('Frequency Response Function')
plt.show()
