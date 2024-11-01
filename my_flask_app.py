from flask import Flask, request #request lets you access incoming request data, including form data and files sent in a POST request
from scipy.io import wavfile
from scipy.signal import stft
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib
import time

matplotlib.use('Agg')#this backend is designed for environments without a display (like a server here). Its allowing me to save plots as files rather than just showing them on screen.
output_directory = '/Users/zachabdallah/Desktop/UAA/fall 2024/A401/Voice-Recorder-master/spectrogram_output'
app = Flask(__name__)#this initializes a Flask app instance. __name__ tells Flask to configure itself based on the name of the current Python module.

# Spectrogram analysis with windowing, DC offset removal, and frequency filtering
def perform_spectrogram_analysis(data, sample_rate, plot_output_path):
    # Remove DC offset by subtracting the mean
    data = data - np.mean(data)#so there was a bunch of noise at like ~300Hz and i had no idea why. This line is subject to removal but it essentially just like normalizes the signal around the mean so that the noise is less prevalent. I will check it out more later.
    #basically though, a DC offset is when a signal oscillates around a non-zero value and so it appears to be shifted up or down as if a constant was added to all values, not providing any meaningful information. By subtracting the mean, we're basically centering the signal around zero.
    #DC offsets are a pretty normal occurence in audio recording/processing.

    # Apply a Hann window to reduce spectral leakage
    window = np.hanning(len(data))
    data = data * window
    #a window function is a mathematical function that is applied to a signal before performing an FFT. When you use FFT, you break a signal up into smaller chunks or "windows". But if the edges of these chunks don't align neatly with the periodic nature of the signal, it can cause artificial frequency components to appear in the result. This is what spectral leakage is: it is essentially a result of the (possible) misalignment of broken up chunks. And so, what Hann windowing does is it tapers the beginning and end of each chunk to zero, such that we keep important information but ensure that it doesn't interfere with other signal chunks. Basically, the frequency transitions will be much much less abrupt and will appear more discrete in a sense. 

    # Compute the Short-Time Fourier Transform (STFT)
    frequencies, times, Zxx = stft(data, fs=sample_rate, nperseg=1024)  # Adjust nperseg as needed

     # Plot the spectrogram
    plt.figure()
    plt.pcolormesh(times, frequencies, np.abs(Zxx), shading='gouraud')
    plt.title('Spectrogram')
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.colorbar(label='Amplitude')

    # Save the plot as an image
    plt.savefig(plot_output_path)
    plt.close()
    
    return Zxx
 

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
    plot_output_path = f'{output_directory}/spectrogram_{timestamp}.png'
    print(f"Saving plot to: {plot_output_path}")
    
    
    # Use perform_spectrogram_analysis instead of perform_fft_analysis
    spectrogram_result = perform_spectrogram_analysis(data, rate, plot_output_path)
    
    # For demonstration, print the first few values of the spectrogram result
    print(f"Sample rate: {rate}")
    print(f"Spectrogram result (first 10 values): {spectrogram_result[:, :10]}")  # Show a sample of the spectrogram data
    
    # Return success message (you can extend this to return the plot or data)
    return "Spectrogram analysis and plot complete", 200#200 means OK


if __name__ == '__main__':#this starts the Flask web server when the script is run. debug=True enables debug mode, which provides helpful error and auto-reloads the server when code changes
    app.run(debug=True)
