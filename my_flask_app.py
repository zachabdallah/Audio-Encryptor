from flask import Flask, request, send_file
from scipy.io import wavfile
from scipy.signal import stft, istft
import numpy as np
import matplotlib.pyplot as plt
import os
import matplotlib 
import time
import hashlib
import warnings
from scipy.io.wavfile import WavFileWarning
matplotlib.use('Agg')#different back end to avoid having to display graphics 
#suppress WavFileWarning
warnings.simplefilter("ignore", WavFileWarning)#scipy doesn't read non-audio chunks which we don't need but it's giving me a warning so we can ignore it.
output_directory = '/Users/zachabdallah/Desktop/UAA/fall 2024/A401/Voice-Recorder-master/spectrogram_output'
app = Flask(__name__)

#README (we're doing work on a matrix called Zxx and it's a complicated object)
#this encryption method uses a Short-Time Fourier Transform (STFT) on the audio data to displays a signal in both the time and frequency domains. By using it, we get a matrix called Zxx, which is a 2D, complex-valued array. It's rows correspond to "frequency bins", and it's columns correspond to "time slices".

#"Frequency bin" means that each row of Zxx correspondsa to a specific frequency range. Heres's how it works:
#the range of frequencies that can be analyzed are from 0 to fs/2 where fs is the sampling rate, and the number of frequency bins (the number of rows in Zxx), is 'nperseg'//2 + 1 (you can change nperseg)
#The spacing between bins is determined by the segment length, where spacing = (fs/nperseg)
#for example, say fs=1000Hz and nperseg = 256, the spacing = 1000/256 = 3.9Hz. That means that the bins, or the rows of Zxx, represent frequencies from 0-3.9Hz, 3.9-7.8Hz, etc., and the number of bins there are is 256/2+1= 129

#"Time slices" are the columns of Zxx, and each column refers to a specific time segment of the signal. 
#When performing the STFT the signal is divided into overlapping segments. The amount of overlap is called "noverlap"
#the number of samples skipped between consecutive segments is the "hop size" = nperseg-noverlap
#The duration of each slice = (hop size/fs), and the number of slices is determined by the length of the signal and the hop size.
#for example, say fs=1000Hz, nperseg = 256, and overlap = 128. Say that the signal also has 1000 samples, hop_size = 256-128 = 128. There will be (1000-128)/128+1=8 times slices, and each time slice has a duration of 128/1000 = 0.128 seconds. 
#Therefore, with fs=1000Hz, nperseg=256, overlap=128, and sample_amount=1000, the shape of Zxx will be (129, 8)

#Each element of Zxx is a complex number that represents the magnitude of the signal AND the phase offset of the signal at a specific location in the matrix. Zxx[x,y] = Magnitude*e^(i*Phase). The phase of an audio signal is sort of like the angular shift of that component at a specific time. We will not be touching the phase.
#we can find the magnitude at all locations of the signal np.abs(Zxx), and we can find the phase by saying np.angle(Zxx)
#And so basically, if we use the example above where Zxx is of size (129, 8) and all that other stuff, and I reference Zxx[67,4], I know that I am referencing a signal that is between 261.3Hz and 265.2Hz, and the sound happened between 0.512 and 0.640 seconds. 
#Now, STFT also generates 1D array called 'frequencies' and 'times'. here's where it all comes together:
#Frequencies.size() is the amount of frequency bins there are, and times.size() is the amount of time sections there are
#Frequencies contains value of all the frequency bins which Zxx uses to reference the ~approximated~ frequency of it's elements based on what row they are in (Zxx[2: ] corresponds to frequencies[2]). So, frequencies[0] = 0Hz, frequencies[1] = 3.9Hz, etc... 
#So basically, you can't reference 3.4Hz here, it will be mapped to the nearest bin which will be read as 3.9Hz, and likewise for 'times'


def get_permutation(length, password):
    # Create a pseudo-random permutation based on the password
    #encode() converts a string into bytes, which the hashing function requires. This byte-string then is made into a seed so that we can make a random number generator whose values are reproducible if we give it the same password later.
    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big') #"big" for big endian
    rng = np.random.default_rng(seed)
    #print(f"Password: {password}, p_Seed: {seed % 10000}")  #debug log
    #permutation is an array of size 'length', whose elements are integers sequentially increasing from 0 to (length-1). This array is then shuffled in place using the rng we made. 
    #ex. permutation[6] = [0, 1, 2, 3, 4, 5] where length = 6
    permutation = np.arange(length)
    rng.shuffle(permutation)
    return permutation

def get_transforms(shape_frequencies, shape_times, password):

    password_hash = hashlib.sha256(password.encode()).digest()
    seed = int.from_bytes(password_hash, 'big')
    rng = np.random.default_rng(seed)
    #in this function, we create two matrices, one for 'times' and one for 'frequencies'. 
    #shape_frequencies is the number of frequency bins Zxx.shape[0], and shape_times is the number of time segments (Zxx.shape[1]). 

    #generate a random array of size Zxx.shape[0] with values uniformly distributed between some range (but reproducible because of our password-seeded rng)
    #then, normalize the matrix by dividing every element by the maximum value in it. This will ensure that the maximum scaling factor is 1.0, keeping the transformations stable and avoiding excessive scaling
    transformation_matrix_frequencies = rng.uniform(0.2, 1.3, shape_frequencies)
    #transformation_matrix_frequencies /= np.max(transformation_matrix_frequencies)#normalize
    #do the same below, but with the time slice matrix
    transformation_matrix_times = rng.uniform(0.2, 29, shape_times)
    #transformation_matrix_times /= np.max(transformation_matrix_times)#normalize

    return transformation_matrix_frequencies, transformation_matrix_times

def shuffle_segments(Zxx, password):
    #This function shuffles the columns of Zxx
    permutation = get_permutation(Zxx.shape[1], password)
    #get permutation based on column amount and password
    #the permutation, which might look like [2,1,5,3,0] for example, represents the new order for the columns in Zxx
    #print("original permutation e\n")
    #print(permutation)
    shuffled_Zxx = Zxx[:, permutation]#rearranges the columns to be ordered like permutation
    return shuffled_Zxx

def unshuffle_segments(Zxx, permutation):
    #get the reverse permutation and rearrange the columns
    #print("original permutation d\n")
    #print(permutation)
    #print("inverse permutation\n")
    inverse_permutation = np.argsort(permutation)#argsort sorts array values from highest to lowest, so it always sorts from 0 to array_length-1
    #print(inverse_permutation)
    unshuffled_Zxx = Zxx[:, inverse_permutation]
    return unshuffled_Zxx


def modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, password):
    #transform only the amplitude, keep phase unchanged
    #Zxx = np.abs(Zxx) * transformation_matrix_frequencies[:, np.newaxis] * transformation_matrix_times[np.newaxis, :] * np.exp(1j * np.angle(Zxx))
    #multiply each row of Zxx by the elements of the frequency transformation array and multiply each column of Zxx by the the time transformations
    #np.exp(1j * np.angle(Zxx) extracts the phase of each element and reconstructs it as a complex exponential so we can make absolute sure that phase is preserved. Now each element in Zxx = Modified_Magnitude*e^(i*original_phase)

    #with all of that said, here is where the actual encryption starts; it's the shuffling. The transformation arrays only affected the amplitude of the elements in Zxx, but that alone is not really a big deal. The frequency and time bins remain fixed throughout this program, as 'frequencies' and 'times' don't change, but the times at which we reference them do: that's the encryption.
    Zxx = shuffle_segments(Zxx, password)
    return Zxx

def undo_modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, permutation):
    #unshuffle segments along the time axis
    Zxx = unshuffle_segments(Zxx, permutation)
    # undo the amplitude transformation, keep phase unchanged
    #Zxx = np.abs(Zxx) / (transformation_matrix_frequencies[:, np.newaxis] * transformation_matrix_times[np.newaxis, :]) * np.exp(1j * np.angle(Zxx))
    return Zxx

#save a spectrogram as a PNG file
def save_spectrogram_image(Zxx, times, frequencies, title, filename):
    plt.figure()

    # Filter Zxx and frequencies to only show up to 3 kHz
    freq_limit = 3000
    freq_indices = frequencies <= freq_limit
    Zxx_limited = Zxx[freq_indices, :]
    frequencies_limited = frequencies[freq_indices]

    # Plot the limited spectrogram
    plt.pcolormesh(times, frequencies_limited, np.abs(Zxx_limited), shading='gouraud')
    plt.title(title)
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.colorbar(label='Amplitude')
    plt.savefig(filename)
    plt.close()
@app.route('/encrypt', methods=['POST'])
def encrypt():
    try:
        print("\nencryption mode:")
        if 'file' not in request.files:
            return "No file part", 400
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        filepath = os.path.join("/tmp", file.filename)
        file.save(filepath)
        
        password = request.form.get('password')
        if not password:
            return "Password is required for encryption", 400

        #read and process the file
        rate, data = wavfile.read(filepath)
        if len(data.shape) == 2:  # Stereo to mono
            data = np.mean(data, axis=1)
        frequencies, times, Zxx = stft(data, fs=rate, nperseg=1024, noverlap = 512)
        
        #log original values
        print(f"-o_STFT Zxx[10,5]: {Zxx[10, 5]}")
        print(f"-o_Zxx[10,5] magnitude: {np.abs(Zxx[10, 5])}")
        print(f"-o_Zxx[10,5] phase: {np.angle(Zxx[10, 5])}")
        print(f"-o_Zxx shape: {Zxx.shape}")
        #log original files
        save_spectrogram_image(Zxx, times, frequencies, 'Original Spectrogram', original_spectrogram_path)
        wavfile.write(original_audio_path, rate, data.astype(np.int16))

        #apply encryption
        transformation_matrix_frequencies, transformation_matrix_times = get_transforms(Zxx.shape[0], Zxx.shape[1], password)
        # Encrypt: Apply amplitude scaling
        scaled_Zxx = np.abs(Zxx) * transformation_matrix_frequencies[:, np.newaxis] * transformation_matrix_times[np.newaxis, :] * np.exp(1j * np.angle(Zxx))

        Zxx = modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, password)
        _, encrypted_data = istft(Zxx, fs=rate, nperseg=1024,noverlap=512)
        data = encrypted_data.astype(np.int16)
        print("--Frequency matrix during encryption:", transformation_matrix_frequencies[5])
        print("--Time matrix during encryption:", transformation_matrix_times[5])

        #log encrypted values
        print(f"-e_Zxx[10,5]: {Zxx[10, 5]}")
        print(f"-e_Zxx[10,5] magnitude: {np.abs(Zxx[10, 5])}")
        print(f"-e_Zxx[10,5] phase: {np.angle(Zxx[10, 5])}")
        print(f"-e_Zxx shape: {Zxx.shape}")
        

        #log encrypted files
        save_spectrogram_image(Zxx, times, frequencies, 'Modified Spectrogram', modified_spectrogram_path)
        wavfile.write(encrypted_audio_path, rate, data.astype(np.int16))

        return send_file(encrypted_audio_path, as_attachment=True, download_name='encrypted_audio.wav'), 200

    except Exception as e:
        print(f"Encryption failed: {e}")
        return "Internal server error", 500

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        print("\ndecryption mode:")
        if 'file' not in request.files:
            return "No file part", 400
        file = request.files['file']
        if file.filename == '':
            return "No selected file", 400
        filepath = os.path.join("/tmp", file.filename)
        file.save(filepath)
        
        password = request.form.get('password')
        if not password:
            return "Password is required for decryption", 400

        #read and process the file
        rate, data = wavfile.read(filepath)
        frequencies, times, Zxx = stft(data, fs=rate, nperseg=1024, noverlap=512)
        
        #log Encrypted values before decryption
        print(f"d_STFT Zxx[10,5] before decryption: {Zxx[10, 5]}")
        
        #apply decryption
        transformation_matrix_frequencies, transformation_matrix_times = get_transforms(Zxx.shape[0], Zxx.shape[1], password)
        permutation = get_permutation(Zxx.shape[1], password)
        restored_Zxx = undo_modify_Zxx(Zxx, transformation_matrix_frequencies, transformation_matrix_times, permutation)
        
        #log restored values
        print(f"-d_Zxx[10,5] after decryption: {restored_Zxx[10, 5]}")
        print(f"-d_Zxx[10,5] magnitude: {np.abs(restored_Zxx[10, 5])}")
        print(f"-d_Zxx[10,5] phase: {np.angle(restored_Zxx[10, 5])}")
        print(f"-d_Zxx shape: {restored_Zxx.shape}")
       

        #check numerical difference
        print(f"Numerical difference at [10,5]: {restored_Zxx[10, 5] - Zxx[10, 5]}")
        if not np.allclose(Zxx, restored_Zxx, atol=1e-6):
            print("Restored Zxx does not match original")
        
        #convert back to time domain
        _, decrypted_data = istft(restored_Zxx, fs=rate, nperseg=1024, noverlap=512)
        data = decrypted_data.astype(np.int16)
       # data = encrypted_data.astype(np.int16)
        print("--Frequency matrix during decryption:", transformation_matrix_frequencies[5])
        print("--Time matrix during decryption:", transformation_matrix_times[5])
        #log restored files
        save_spectrogram_image(restored_Zxx, times, frequencies, 'Restored Spectrogram', restored_spectrogram_path)
        wavfile.write(decrypted_audio_path, rate, data.astype(np.int16))

        return send_file(decrypted_audio_path, as_attachment=True, download_name='decrypted_audio.wav'), 200

    except Exception as e:
        print(f"Decryption failed: {e}")
        return "Internal server error", 500

if __name__ == '__main__':
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    #spectrogram paths
    original_spectrogram_path = f'{output_directory}/original_spectrogram_{timestamp}.png'
    modified_spectrogram_path = f'{output_directory}/modified_spectrogram_{timestamp}.png'
    restored_spectrogram_path = f'{output_directory}/restored_spectrogram_{timestamp}.png'
    #audio paths
    original_audio_path = f'{output_directory}/original_audio_{timestamp}.wav'
    encrypted_audio_path = f'{output_directory}/encrypted_audio_{timestamp}.wav'
    decrypted_audio_path = f'{output_directory}/restored_audio_{timestamp}.wav'
    
    app.run(debug=True)
