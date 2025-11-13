#include <Arduino.h>
#include <cstring>
const String firmware            = "3.1 (M_1024, matchbox test)";      // firmware version

#include <SPI.h>

//galvos
const byte CS     = 12; 
const byte CLOCK  = 13;
const byte DATA   = 11;
//stage
const byte Xo     = 31;
const byte Yo     = 29;
const byte Zo     = 27;
const byte Xi     = 32;
const byte Yi     = 30;
const byte Zi     = 28;

//digital I/O
const byte CamOut               = 40;
const byte CamIn                = 22;
const byte temp_monitor         = A9;
const byte trigger_Filter       = 16;
const byte test_output          = 35;

const byte L405          = 25;
const byte L488          = 24;
const byte L520          = 4;
const byte L638          = 5;
const byte MaiTai        = 7;
int    laser_pin         = MaiTai;

//LED power
uint16_t LED_power = 20;  //0-50 is useable range


volatile bool stage_ready_flag  = true;     // flag denoting when stage moves are complete
volatile bool camera_ready_flag = true;     // flag denotes when camera has returned a 'readout complete' signal
volatile bool filter_ready_flag = false;    // flag denotes when filter has returned a 'movement complete' signal


uint16_t slice_counter          = 0;        // for tracking slices through a z-stack
uint16_t nZ                     = 0;        // for storing total number of slices in a z-stack

bool z_stacking                 = false;    // flag denotes when z-stack is taking place
bool scanning                   = false;    // flag denotes when continuous scanning is taking place
bool musical                    = false;    // keeps track of if in musical imaging mode (no z trigger)

uint16_t park                   = 0;        // galvo position to park the beam when not imaging
uint32_t exposure               = 0;        // keep track of camera exposure
uint8_t cam_delay               = 0;        // trigger scanner this time after trigger camera
const byte HALF_CLOCK_PERIOD    = 1;        // 2 uS of clock period 


uint16_t g_enter_step           = 174;       // galvo step at which beam enters the camera FOV
uint16_t g_exit_step            = 861;      // galvo step at which beam leaves the camera FOV
uint16_t g_steps_per_FOV        = (g_exit_step - g_enter_step); // number of steps on the galvo that corresponds to the full FOV of the camera

float temp_offset = 0.0;


void setup() {  
  
  pinMode(L405, OUTPUT);
  pinMode(L488, OUTPUT);
  pinMode(L520, OUTPUT);
  pinMode(L638, OUTPUT);
  pinMode(MaiTai, OUTPUT);
  digitalWrite(L405, 0);
  digitalWrite(L488, 0);
  digitalWrite(L520, 0);
  digitalWrite(L638, 0);

  analogReadResolution(12);
  analogWriteResolution(8);

  Serial.begin(115200);
  while (!Serial) {;}  // Wait for Serial to be ready
  Serial.println("DIL ready to receive commands.");
  SPI.begin();
//  pinMode(DATA, OUTPUT);
//  pinMode(CLOCK, OUTPUT);
  pinMode(CS, OUTPUT);
  digitalWrite(CS, HIGH);
//  digitalWrite(DATA, LOW);
//  digitalWrite(CLOCK, LOW);
  pinMode(Xo, OUTPUT);
  pinMode(Yo, OUTPUT);
  pinMode(Zo, OUTPUT);
  pinMode(Xi, INPUT_PULLUP);
  pinMode(Yi, INPUT_PULLUP);
  pinMode(Zi, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(Zi), z_move_complete, RISING);
  
  pinMode(CamIn, INPUT);
  attachInterrupt(digitalPinToInterrupt(CamIn), camera_ready, RISING);

  pinMode(CamOut, OUTPUT);
  digitalWrite(CamOut, LOW);

  pinMode(trigger_Filter, INPUT);
  attachInterrupt(digitalPinToInterrupt(trigger_Filter), filter_ready, RISING);
  
  pinMode(temp_monitor, INPUT);
  
  pinMode(test_output, OUTPUT);
  digitalWrite(test_output, HIGH);

  set_galvo(park);

}

void z_move_complete()  {stage_ready_flag    = true;}
void camera_ready()     {camera_ready_flag   = true;}
void filter_ready()     {filter_ready_flag   = true;}

int getLaserPin(const String& wavelength) {
    if (wavelength == "405") return L405;
    if (wavelength == "488") return L488;
    if (wavelength == "520") return L520;
    if (wavelength == "638") return L638;
    return MaiTai;  // Unknown wavelength, e.g. NIR, direct  to a non-connected pin
}

void parseCommand(String command) {
  Serial.print("incoming command --> ");Serial.println(command);
  command.trim();
  // Ensure the command starts with a forward slash
  if (command[0] != '/') {
    Serial.println("Invalid command format... ");
    return;
  }

  // Remove the forward slash and semicolon
  command.remove(0, 1);
  command.remove(command.length() - 1, 1);

  // Split the command into parts using '.' as the delimiter
  int firstDotIndex = command.indexOf('.');
  String word = command.substring(0, firstDotIndex);
  command.remove(0, firstDotIndex + 1);

  int values[4] = {0};
  int valueIndex = 0;
  while (command.length() > 0 && valueIndex < 4) {
    int dotIndex = command.indexOf('.');
    if (dotIndex == -1) {
      values[valueIndex] = command.toInt();
      command = "";
    } else {
      values[valueIndex] = command.substring(0, dotIndex).toInt();
      command.remove(0, dotIndex + 1);
    }
    valueIndex++;
  }

  // Determine which function to call based on the word
  if (word == "stack") {
    scanning = false;
    z_stacking  = true;
    
    //initially set scanner to 0
    set_galvo(park);
    delay(20);
    //set up for z-stack
    exposure    = values[0];
    nZ          = values[1];

    laser_pin = getLaserPin(values[2]);

    Serial.print("entering z-stack mode, wav: ");
    Serial.print(values[2]);
    Serial.print("; nZ: ");
    Serial.print(nZ);
    Serial.print("; exp: ");
    Serial.println(exposure);
  
  } else if (word == "musical") {
    Serial.print("Setting Musical Mode: ");
    if(values[0]==1){musical = true; Serial.println("True");}
    if(values[0]==0){musical = false; Serial.println("False");}
  
  } else if (word == "hello") {
    Serial.print("Dual Illumination Lightsheet, firmware v: ");Serial.println(firmware);
  
  } else if (word == "scan") {
    Serial.println("entering scan mode");
    
    exposure  = values[0];
    laser_pin = getLaserPin(values[1]);
    Serial.println(exposure);
    Serial.println(laser_pin);

    z_stacking  = false;
    scanning  = true;
  
  } else if (word == "delay") {
    Serial.println("setting cam trigger delay");
    cam_delay   = values[0];
  
  } else if (word == "filter") {
    Serial.println("waiting for filter movement");
    filter_ready_flag = false;

  } else if (word == "stop") {
    digitalWriteFast(L405, 0);
    digitalWriteFast(L488, 0);
    digitalWriteFast(L520, 0);
    digitalWriteFast(L638, 0);
    set_galvo(park);
    z_stacking  = false;
    scanning    = false;

    Serial.println("stopping");

  } else if (word == "405") {
    Serial.print("405 laser ");Serial.println(values[0]);
    digitalWrite(L405,values[0]);
    
  } else if (word == "488") {
    Serial.print("488 laser ");Serial.println(values[0]);
    digitalWrite(L488,values[0]);
    
  } else if (word == "520") {
    Serial.print("520 laser ");Serial.println(values[0]);
    digitalWrite(L520,values[0]);
    
  } else if (word == "638") {
    Serial.print("638 laser ");Serial.println(values[0]);
    digitalWrite(L638,values[0]);
    
  } else if (word == "Shutter") {
    Serial.print("All visible lasers Off ");Serial.println();
    laser_pin = MaiTai;
    digitalWrite(L405,0);
    digitalWrite(L488,0);
    digitalWrite(L520,0);
    digitalWrite(L638,0);
    
  } else if (word == "galvo") {
    Serial.print("galvo to ");Serial.println(values[0]);
    z_stacking  = false;
    scanning    = false;
    set_galvo(values[0]);

  } else if (word == "temp") {
    Serial.print("Temp:");
    int rawValue = analogRead(temp_monitor);         // Read raw ADC value
    float voltage = (rawValue / 4095.0) * 3.3;    // Convert to voltage
    float temperatureC = (voltage / 5.0) * 60.0;  // Convert to temperature
    Serial.print(rawValue);
    Serial.print(", ");
    Serial.print(voltage, 3);
    Serial.print(", ");
    Serial.println(temperatureC, 1);

  } else {
    Serial.println("Unknown command");
  }
}

void z_slice(uint32_t exposure){ //do a single slice within a z-stack, exposure in ms

  //calculate galvo step time
  float s_t = (exposure * 1000.0) / g_steps_per_FOV; //s_t: (us) exposure time spread over the number of galvo steps in the camera FOV 

  uint32_t prev_micros = 0;
  

// step times <2µs can't be written to the DAC fast enough, need to increase step time and decrease DAC resolution

  uint32_t s_t_int = int(s_t);

//need to trigger camera 9 * line interval microseconds before g_start_step
  float line_interval = (exposure / 1024); //line interval = exposure/no. of pixel lines
  float cam_delay_steps = ((1 * line_interval) / s_t) + 1; //how many galvo steps before g_enter_step to trigger CAM (plus one to ensure rounding up)
  int cam_trigger_step = g_enter_step - int(cam_delay_steps);
  // digitalWriteFast(laser_pin, HIGH);
  digitalWriteFast(CamOut,LOW);
  //SCAN
  for(int g=0;g<1024;g++){
    if(g==cam_trigger_step)     {
      digitalWriteFast(laser_pin, HIGH);
      digitalWriteFast(CamOut, HIGH); 
      camera_ready_flag = false; }  // trigger camera 9 * line interval (us) before beam enters FOV
    if(g==g_exit_step){digitalWriteFast(laser_pin, LOW);}
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(g);

  }
  digitalWriteFast(CamOut, LOW);
  // digitalWriteFast(laser_pin, LOW);
  if(z_stacking && musical == false){
    //start stage movement
    digitalWriteFast(Zo,HIGH);
    delayMicroseconds(1);
    digitalWriteFast(Zo,LOW);
    stage_ready_flag = false;
  }
  set_galvo(0);                     // return galvo to zero position ready for next scan
}


void check_serial(){
  static String commandBuffer = "";

  // Read incoming serial data
  while (Serial.available() > 0) {
    char incomingByte = Serial.read();

    // Add the incoming character to the buffer
    commandBuffer += incomingByte;

    // Check if the command ends with a semicolon
    if (incomingByte == ';') {
      parseCommand(commandBuffer);
      commandBuffer = ""; // Clear buffer for the next command
    }
  }
}


void loop() {
  check_serial();
  if(musical){stage_ready_flag=true;}
  if(z_stacking  && camera_ready_flag  &&  stage_ready_flag){    //enter when stage and camera flags are set
    
    z_slice(exposure);                                  // take a slice
    slice_counter++;
    Serial.print("z:");Serial.println(slice_counter);
    if(slice_counter >= nZ){                            // check if stack complete
      z_stacking = false;                               // stop z-stacking
      slice_counter = 0;                                // reset slice counter
      set_galvo(park);
    }
  }

  if(scanning && camera_ready_flag){                    // start next scan when camera finished readout
    z_slice(exposure);
  }

  if(filter_ready_flag == true){
    filter_ready_flag = false;
    Serial.println("Filter_True");
  }
}

void set_galvo(uint16_t value){
  value = (value & 0x3ff) << 2;
  SPI.beginTransaction(SPISettings(14000000, MSBFIRST, SPI_MODE0));
  digitalWriteFast(CS, LOW);
  SPI.transfer16(value);
  digitalWriteFast(CS, HIGH);
  SPI.endTransaction();
}