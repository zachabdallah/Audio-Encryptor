from flask import Flask, request #request lets you access incoming request data, including form data and files sent in a POST request
from scipy.io import wavfile
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib
import time
#so an FFT (Fast Fourrier Transform) is an algorithm used to compute the DFT (Discrete Dourier Transform) but is just way faster and more efficient. Basically, it converts a signal from its time domain into its frequency domain, which shows all of the different frequencies (along with their magnitudes) that make up a signal. Its time complexity is O(NlogN)
#The idea behind a Fourier Transform is that any complex signal can be broken down into a combination of different frequencies present in the signal. A signals frequency domain is like its fingerprint, basically.
#Now then, with our frequency domain for a signal, we can manipulate those frequency components, such as swapping the bands or introducing noise in some areas. We could even leave some bands in tact, and we'd pick them randomly based on the key used for encryption. 
#This covers the "change the pitch" part of the encryption. We can also switch around time slices of the original signal but that just requires the .wav file.

matplotlib.use('Agg')#this backend is designed for environments without a display (like a server here). Its allowing me to save plots as files rather than just showing them on screen.
output_directory = '/Users/zachabdallah/Desktop/UAA/fall 2024/A401/Voice-Recorder-master/fft_output'
app = Flask(__name__)#this initializes a Flask app instance. __name__ tells Flask to configure itself based on the name of the current Python module.

# FFT analysis with windowing, DC offset removal, and frequency filtering
def perform_fft_analysis(data, sample_rate, plot_output_path):
    # Remove DC offset by subtracting the mean
    data = data - np.mean(data)#so there was a bunch of noise at like ~300Hz and i had no idea why. This line is subject to removal but it essentially just like normalizes the signal around the mean so that the noise is less prevalent. I will check it out more later.
    #basically though, a DC offset is when a signal oscillates around a non-zero value and so it appears to be shifted up or down as if a constant was added to all values, not providing any meaningful information. By subtracting the mean, we're basically centering the signal around zero.
    #DC offsets are a pretty normal occurence in audio recording/processing.

    # Apply a Hann window to reduce spectral leakage
    window = np.hanning(len(data))
    data = data * window
    #a window function is a mathematical function that is applied to a signal before performing an FFT. When you use FFT, you break a signal up into smaller chunks or "windows". But if the edges of these chunks don't align neatly with the periodic nature of the signal, it can cause artificial frequency components to appear in the result. This is what spectral leakage is: it is essentially a result of the (possible) misalignment of broken up chunks. And so, what Hann windowing does is it tapers the beginning and end of each chunk to zero, such that we keep important information but ensure that it doesn't interfere with other signal chunks. Basically, the frequency transitions will be much much less abrupt and will appear more discrete in a sense. 

    # Number of samples
    n = len(data)

    # Apply FFT
    fft_out = np.fft.fft(data)

    # Only keep the positive frequencies
    fft_out = fft_out[:n // 2]  # Ok so for some reason, fft mirrors itself over the sample rate, so like around 44kHz for us I think, and here I'm just removing that cuz I don't see a use for that now. This mirror was treated as "negative frequencies" so we're removing those.

    #Compute the frequency bins
    #FFT splits the frequency spectrums into a number of discrete intervals called bins. Here we have n bins, where n is the number of samples we have. 'd' is obviously the distance between bins.
    frequencies = np.fft.fftfreq(n, d=1/sample_rate)
    frequencies = frequencies[:n // 2]  #like the FFT results, we're only keeping the first half of the frequency bins

    # Filter to show only frequencies between 0 and 1000 Hz
    freq_limit = 1000  # 1kHz limit for now just for better visualization
    indices = np.where(frequencies <= freq_limit)#this just identifies valid frequencies for us now (0-1kHz)
    filtered_frequencies = frequencies[indices]#extract valid frequencies
    filtered_fft_out = fft_out[indices]#extract corresponding fft values from these relevant frequencies

    # Plot the frequencies between 0 and 1000 Hz
    plt.figure()
    plt.plot(filtered_frequencies, np.abs(filtered_fft_out))
    plt.title('Frequency Spectrum (0-1 kHz)')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Amplitude')

    # Save the plot as an image
    plt.savefig(plot_output_path)
    plt.close()
    
    return filtered_fft_out

@app.route('/analyze', methods=['POST'])#this creates a rout (/analyze) for the Flask app that will accept POST requests. It is used for uploading an audio file to be analyzed
def analyze():
    if 'file' not in request.files:
        return "No file part", 400 #400 means bad request

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    filepath = os.path.join("/tmp", file.filename)#create a temporary file path for saving the uploaded audio file
    file.save(filepath)

    # Read the WAV file
    rate, data = wavfile.read(filepath)#sample rate goes to rate and data goes to data
    
    # Check if the audio data is stereo (2 channels), convert to mono if necessary
    if len(data.shape) == 2:
        data = np.mean(data, axis=1)  # Convert stereo to mono by averaging the channels
    
    # Define where to save the plot
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    plot_output_path = f'{output_directory}/fft_{timestamp}.png'
    print(f"Saving plot to: {plot_output_path}")
    
    # Perform FFT analysis and save the plot
    fft_result = perform_fft_analysis(data, rate, plot_output_path)
    
    # For demonstration, print the first few values of the FFT result
    print(f"Sample rate: {rate}")
    print(f"FFT result (first 10 values): {fft_result[:10]}")
    
    # Return success message (you can extend this to return the plot or data)
    return "FFT analysis and plot complete", 200#200 means OK


if __name__ == '__main__':#this starts the Flask web server when the script is run. debug=True enables debug mode, which provides helpful error and auto-reloads the server when code changes
    app.run(debug=True)
