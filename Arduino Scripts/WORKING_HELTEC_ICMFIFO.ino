#include <SPI.h>
#include <ICM42688.h>

// Pin definitions for SPI connection
#define ICM_CS 34  // Chip Select for the accelerometer
#define ICM_SCK 36  // SPI Clock pin
#define ICM_MISO 33  // SPI MISO pin
#define ICM_MOSI 35  // SPI MOSI pin
#define INTERRUPT_PIN 20

// ICM42688 object with the sensor on SPI bus 0 and chip select pin
ICM42688 imu(SPI, ICM_CS);

volatile bool dataReady = false;

// Buffer settings
const int bufferscale = 17500;  // Buffer size for storing data
float ax[bufferscale], ay[bufferscale], az[bufferscale];  // Accelerometer buffer
unsigned long timestamps[bufferscale];  // Timestamp buffer

void setup() {
    // Initialize Serial communication
    Serial.begin(460800);
    while (!Serial) {}

    // Initialize SPI with the defined pins
    SPI.begin(ICM_SCK, ICM_MISO, ICM_MOSI, ICM_CS);

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
        ax[i] = imu.accX();
        ay[i] = imu.accY();
        az[i] = imu.accZ();
        timestamps[i] = micros();  // Capture timestamp
    }

    // Output all buffered data at once
    for (int i = 0; i < bufferscale; i++) {
        // Use sprintf to format the data into a string
        char buffer[50];
        sprintf(buffer, "1 %lu\t%.6f\t%.6f\t%.6f\t", 
                timestamps[i], ax[i], ay[i], az[i]);

        // Print the entire formatted string
        Serial.println(buffer);
    }
}

// Interrupt handler for IMU data ready signal
void setImuFlag() {
    dataReady = true;
}



/* Semaphore test?

#include <SPI.h>
#include <ICM42688.h>

// Pin definitions for SPI connection
#define ICM_CS 34  // Chip Select for the accelerometer
#define ICM_SCK 36  // SPI Clock pin
#define ICM_MISO 33  // SPI MISO pin
#define ICM_MOSI 35  // SPI MOSI pin
#define INTERRUPT_PIN 20

// ICM42688 object with the sensor on SPI bus 0 and chip select pin
ICM42688 imu(SPI, ICM_CS);

volatile bool dataReady = false;

// Buffer settings
const int bufferscale = 100;  // Buffer size for storing data
float ax[bufferscale], ay[bufferscale], az[bufferscale];  // Accelerometer buffer
float gx[bufferscale], gy[bufferscale], gz[bufferscale];  // Gyroscope buffer
unsigned long timestamps[bufferscale];  // Timestamp buffer

SemaphoreHandle_t dataSemaphore;  // Semaphore to signal data is ready to print
volatile bool bufferFull = false;  // Flag to indicate when buffer is full

// Task handles
TaskHandle_t dataCollectionTask;
TaskHandle_t dataOutputTask;

void setup() {
    // Initialize Serial communication
    Serial.begin(460800);
    while (!Serial) {}

    // Initialize SPI with the defined pins
    SPI.begin(ICM_SCK, ICM_MISO, ICM_MOSI, ICM_CS);

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

    // Initialize the semaphore
    dataSemaphore = xSemaphoreCreateBinary();

    // Create tasks for data collection and data output, assign them to different cores
    xTaskCreatePinnedToCore(collectData, "Data Collection", 10000, NULL, 1, &dataCollectionTask, 0);  // Run on core 0
    xTaskCreatePinnedToCore(printData, "Data Output", 10000, NULL, 1, &dataOutputTask, 1);            // Run on core 1

    Serial.println("ax,ay,az,gx,gy,gz,timestamp");
}

void loop() {
    // Main loop does nothing, tasks handle everything
}

// Task: Collect data from the IMU (runs on core 0)
void collectData(void *pvParameters) {
    while (1) {
        // Collect data for the defined buffer size
        for (int i = 0; i < bufferscale; i++) {
            // Wait until data is ready

            
            while (!dataReady) {
                vTaskDelay(1);  // Yield to avoid WDT reset
            }
            dataReady = false;
            

            // Read the sensor data
            imu.getAGT();
          

            // Store accelerometer, gyroscope, and timestamp data in buffers
            ax[i] = imu.accX();
            ay[i] = imu.accY();
            az[i] = imu.accZ();
            gx[i] = imu.gyrX();
            gy[i] = imu.gyrY();
            gz[i] = imu.gyrZ();
            timestamps[i] = micros();  // Capture timestamp
        }

        // Signal that the buffer is full
        bufferFull = true;
        xSemaphoreGive(dataSemaphore);  // Signal to the printing task
    }
}

// Task: Print data to Serial (runs on core 1)
void printData(void *pvParameters) {
    while (1) {
        // Wait until buffer is full
        if (xSemaphoreTake(dataSemaphore, portMAX_DELAY)) {
            if (bufferFull) {
                // Output all buffered data at once
                for (int i = 0; i < bufferscale; i++) {
                    // Use sprintf to format the data into a string
                    char buffer[100];
                    sprintf(buffer, "%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%.6f\t%lu", 
                            ax[i], ay[i], az[i], gx[i], gy[i], gz[i], timestamps[i]);

                    // Print the entire formatted string
                    Serial.println(buffer);
                }

                bufferFull = false;  // Reset the buffer flag
            }
        }
    }
}

// Interrupt handler for IMU data ready signal
void setImuFlag() {
    dataReady = true;
}
*/