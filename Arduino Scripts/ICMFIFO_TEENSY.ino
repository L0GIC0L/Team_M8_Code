#include <SPI.h>
#include <ICM42688.h>

// Pin definitions for SPI connection
#define ICM_CS 10  // Chip Select for the accelerometer
#define INTERRUPT_PIN 32  // Interrupt pin for IMU data ready

// ICM42688 object with the sensor on SPI bus 0 and chip select pin
ICM42688 imu(SPI, ICM_CS);

volatile bool dataReady = false;
unsigned int transmissionDelay = 400;  // Default delay for transmission in microseconds

void setup() {
    // Initialize Serial communication
    Serial.begin(460800);  // Fast serial communication
    Serial.println("System online...");
    while (!Serial) {}  // Wait for serial to initialize (if needed)

    // Prompt the user to input the transmission delay
    Serial.println("Enter transmission speed delay in microseconds (default: 400): ");
    while (!Serial.available()) {}  // Wait for user input

    // Read the user input and convert to an integer
    transmissionDelay = Serial.parseInt();
    if (transmissionDelay <= 0) {
        transmissionDelay = 400;  // Use default if invalid input
    }
    Serial.print("Transmission speed set to: ");
    Serial.println(transmissionDelay);

    // Initialize SPI - Teensy 4.1 uses default SPI pins (13-SCK, 12-MISO, 11-MOSI)
    SPI.begin();

    // Start communication with IMU
    int status = imu.begin();
    if (status < 0) {
        while (1) {}  // Halt if IMU fails to initialize
    }

    // Attach interrupt to data ready pin
    pinMode(INTERRUPT_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), setImuFlag, RISING);

    // Set output data rate for accelerometer
    imu.setAccelODR(ICM42688::odr4k);  // Max data rate for fast sampling

    // Enable data ready interrupt
    imu.enableDataReadyInterrupt();
}

char output[100];

void loop() {
    // Check if there's incoming data for new transmission delay or commands
    if (Serial.available() > 0) {
        int newDelay = Serial.parseInt();  // Read input as integer
        if (newDelay > 0) {
            transmissionDelay = newDelay;
            Serial.print("Transmission delay updated to: ");
            Serial.println(transmissionDelay);
        }
    }

    // Wait until data is ready
    while (!dataReady) {}
    dataReady = false;

    // Read the sensor data
    imu.getAGT();

    // Get accelerometer values and timestamp
    float ax = imu.accX();
    float ay = imu.accY();
    float az = imu.accZ();
    unsigned long timestamp = micros();  // Capture timestamp

    // Minimize serial output
    sprintf(output, "1 %.1lu %.6f %.6f %.6f\n", timestamp, ax, ay, az);

    // Print timestamp followed by accelerometer data (3 decimal places, compact format)
    if (Serial.availableForWrite() > 100 * 8) {
        Serial.print(output);
    }

    // Use user-defined delay for transmission speed
    delayMicroseconds(transmissionDelay);
}

// Interrupt handler for IMU data ready signal
void setImuFlag() {
    dataReady = true;
}

/*

#include <SPI.h>
#include <ICM42688.h>

// Pin definitions for SPI connection
#define ICM_CS 10  // Chip Select for the accelerometer
#define INTERRUPT_PIN 32  // Interrupt pin for IMU data ready

// ICM42688 object with the sensor on SPI bus 0 and chip select pin
ICM42688 imu(SPI, ICM_CS);

volatile bool dataReady = false;

// Buffer settings
const int bufferscale = 35500;  // Buffer size for storing data
//float ax[bufferscale], ay[bufferscale], az[bufferscale];  // Accelerometer buffer
float az[bufferscale];  // Accelerometer buffer
unsigned long timestamps[bufferscale];  // Timestamp buffer

void setup() {
    // Initialize Serial communication
    Serial.begin(460800);
    while (!Serial) {}

    // Initialize SPI with the defined pins
    SPI.begin();

    // Start communication with IMU
    int status = imu.begin();
    if (status < 0) {
        Serial.println("IMU initialization unsuccessful");
        Serial.println("Check IMU wiring or try cycling power");
        Serial.print("Status: ");
        Serial.println(status);
        while (1) {}
    }

    // Attach interrupt to data ready pin
    pinMode(INTERRUPT_PIN, INPUT);
    attachInterrupt(digitalPinToInterrupt(INTERRUPT_PIN), setImuFlag, RISING);

    // Set output data rate for accelerometer and gyroscope
    imu.setAccelODR(ICM42688::odr4k);
    imu.setGyroODR(ICM42688::odr4k);

    // Enable data ready interrupt
    imu.enableDataReadyInterrupt();

    Serial.println("ax,ay,az,gx,gy,gz,timestamp");
}

void loop() {
    // Collect data for the defined buffer size
    for (int i = 0; i < bufferscale; i++) {
        // Wait until data is ready
        while (!dataReady) {}
        dataReady = false;

        // Read the sensor data
        imu.getAGT();

        // Store accelerometer, gyroscope, and timestamp data in buffers
        //ax[i] = imu.accX();
        //ay[i] = imu.accY();
        az[i] = imu.accZ();
        timestamps[i] = micros();  // Capture timestamp
    }

    // Output all buffered data at once
    for (int i = 0; i < bufferscale; i++) {
        // Use sprintf to format the data into a string
        char buffer[50];
        //sprintf(buffer, "1 %lu\t%.6f\t%.6f\t%.6f\t", 
                //timestamps[i], ax[i], ay[i], az[i]);

        sprintf(buffer, "1 %lu\t 0 0 %.6f\t", 
                timestamps[i], az[i]);

        // Print the entire formatted string
        Serial.println(buffer);
        delay(0.01);
    }
}

// Interrupt handler for IMU data ready signal
void setImuFlag() {
    dataReady = true;
} */