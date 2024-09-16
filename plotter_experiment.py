#include <Adafruit_Sensor.h>
#include <Adafruit_ADXL343.h>

#define ADXL343_SCK 13
#define ADXL343_MISO 12
#define ADXL343_MOSI 11
#define ADXL343_CS 53
#define ADXL343_CS2 40

//Adafruit_ADXL343 accel = Adafruit_ADXL343(ADXL343_SCK, ADXL343_MISO, ADXL343_MOSI, ADXL343_CS, 12345);

Adafruit_ADXL343 accel = Adafruit_ADXL343(ADXL343_CS, &SPI, 12345);
Adafruit_ADXL343 accel2 = Adafruit_ADXL343(ADXL343_CS2, &SPI, 12345);

const int bufferscale = 10;
int16_t x4[bufferscale], y4[bufferscale], z4[bufferscale];
int16_t x3[bufferscale], y3[bufferscale], z3[bufferscale];
unsigned long time1[bufferscale];  // Use unsigned long for timestamp storage
unsigned long time2[bufferscale];  // Use unsigned long for timestamp storage

void displayRange(void)
{
  Serial.print("Range:         +/- ");
  switch(accel.getRange())
  {
    case ADXL343_RANGE_16_G: Serial.print("16 "); break;
    case ADXL343_RANGE_8_G: Serial.print("8 "); break;
    case ADXL343_RANGE_4_G: Serial.print("4 "); break;
    case ADXL343_RANGE_2_G: Serial.print("2 "); break;
    default: Serial.print("?? "); break;
  }
  Serial.println(" g");
}

void displayDataRate(void)
{
  Serial.print("Data Rate:    ");
  switch(accel.getDataRate())
  {
    case ADXL343_DATARATE_3200_HZ: Serial.print("3200 "); break;
    case ADXL343_DATARATE_1600_HZ: Serial.print("1600 "); break;
    case ADXL343_DATARATE_800_HZ: Serial.print("800 "); break;
    case ADXL343_DATARATE_400_HZ: Serial.print("400 "); break;
    case ADXL343_DATARATE_200_HZ: Serial.print("200 "); break;
    case ADXL343_DATARATE_100_HZ: Serial.print("100 "); break;
    case ADXL343_DATARATE_50_HZ: Serial.print("50 "); break;
    case ADXL343_DATARATE_25_HZ: Serial.print("25 "); break;
    case ADXL343_DATARATE_12_5_HZ: Serial.print("12.5 "); break;
    case ADXL343_DATARATE_6_25HZ: Serial.print("6.25 "); break;
    case ADXL343_DATARATE_3_13_HZ: Serial.print("3.13 "); break;
    case ADXL343_DATARATE_1_56_HZ: Serial.print("1.56 "); break;
    case ADXL343_DATARATE_0_78_HZ: Serial.print("0.78 "); break;
    case ADXL343_DATARATE_0_39_HZ: Serial.print("0.39 "); break;
    case ADXL343_DATARATE_0_20_HZ: Serial.print("0.20 "); break;
    case ADXL343_DATARATE_0_10_HZ: Serial.print("0.10 "); break;
    default: Serial.print("???? "); break;
  }
  Serial.println(" Hz");
}

const uint8_t ACCEL1_ID = 1;
const uint8_t ACCEL2_ID = 2;

void setup(void)
{
  Serial.begin(1000000);
  while (!Serial);
  Serial.println("Accelerometer Test"); Serial.println("");

  if(!accel.begin())
  {
    Serial.println("Ooops, no ADXL343 detected ... Check your wiring!");
    while(1);
  }


  if(!accel2.begin())
  {
    Serial.println("RUN!");
    while(1);
  }

  accel.setRange(ADXL343_RANGE_16_G);
  accel.setDataRate(ADXL343_DATARATE_3200_HZ);

  accel2.setRange(ADXL343_RANGE_16_G);
  accel2.setDataRate(ADXL343_DATARATE_3200_HZ);

  accel.printSensorDetails();
  displayDataRate();
  displayRange();
  Serial.println("");
}

void loop(void) {
  int loop = 0;

  // Collect data 10 times
  for (int loop = 0; loop < bufferscale; loop++) {
    accel.getXYZ(x3[loop], y3[loop], z3[loop]);
    time1[loop] = micros();  // Capture timestamp for each reading
    accel2.getXYZ(x4[loop], y4[loop], z4[loop]);
    time2[loop] = micros();  // Capture timestamp for each reading
  }

  String output = "";
  for (int i = 0; i < bufferscale; i++) {
    output += "1 " + String(time1[i]) + " " + x3[i] + " " +y3[i] + " " + z3[i] + "\n" + "2 " + String(time2[i]) + " " + x4[i] + " " + y4[i] + " " + z4[i] + "\n";
  }

  Serial.println(output);

}
