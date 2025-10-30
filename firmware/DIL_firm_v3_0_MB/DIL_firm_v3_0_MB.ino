// scanning and z-stacking working?



#include <Arduino.h>
const String firmware            = "3.0 (M_1024, Matchbox)";      // firmware version


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
const byte trigger_LED          = 23;
const byte trigger_Filter       = 16;
const byte test_output          = 35;


//Laser 
#include "imxrt.h"

constexpr float PWM_FREQ_TARGET = 3.56e6;  // ≈ actual with 6-bit
constexpr float F_BUS_EXPECTED  = 228e6;   // Bus freq at 912 MHz CPU
constexpr uint16_t MOD = 63;               // 6-bit resolution (0–63)

//LED power
uint16_t LED_power = 20;  //0-50 is useable range

//Flags
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

void setup() {
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
  
  pinMode(trigger_LED, OUTPUT);
  digitalWrite(trigger_LED, HIGH);
  
  pinMode(test_output, OUTPUT);
  digitalWrite(test_output, HIGH);

  set_galvo(park);

//~~~~~~~~~~~~~~~ LASER FAST PWM SETUP CODE ~~~~~~~~~~~~~~~//
  CORE_PIN24_CONFIG = 1;  // PWM2_A0
  CORE_PIN25_CONFIG = 1;  // PWM2_B0
  CORE_PIN4_CONFIG  = 1;  // PWM2_B2
  CORE_PIN5_CONFIG  = 1;  // PWM2_A2

  CCM_CCGR4 |= CCM_CCGR4_FLEXPWM2(CCM_CCGR_ON);  // enable clock

  // Disable before setup
  FLEXPWM2_MCTRL |= FLEXPWM_MCTRL_CLDOK(0xF);
  FLEXPWM2_MCTRL &= ~FLEXPWM_MCTRL_RUN(0xF);

  // Configure two submodules: SM0 and SM2
  for (int sm : {0, 2}) {
    auto &S = FLEXPWM2.SM[sm];
    S.INIT  = 0;
    S.VAL0  = 0;
    S.VAL1  = MOD;  // Period

    // start 50% duty for A/B
    uint16_t half = MOD / 2;
    S.VAL2 = 0;
    S.VAL3 = half;  // channel A
    S.VAL4 = 0;
    S.VAL5 = half;  // channel B

    S.CTRL2 = FLEXPWM_SMCTRL2_CLK_SEL(0);  // use IPBus clock
    S.CTRL  = FLEXPWM_SMCTRL_PRSC(0);      // prescaler /1
  }
// Enable outputs
  FLEXPWM2_OUTEN =
      FLEXPWM_OUTEN_PWMA_EN((1 << 0) | (1 << 2)) |
      FLEXPWM_OUTEN_PWMB_EN((1 << 0) | (1 << 2));

  // Load and run
  FLEXPWM2_MCTRL |= FLEXPWM_MCTRL_LDOK((1 << 0) | (1 << 2));
  FLEXPWM2_MCTRL |= FLEXPWM_MCTRL_RUN((1 << 0) | (1 << 2));
  
//~~~~~~~~~~~~~~~ end LASER FAST PWM SETUP ~~~~~~~~~~~~~~~//
}

void z_move_complete()  {stage_ready_flag    = true;}
void camera_ready()     {camera_ready_flag   = true;}
void filter_ready()     {filter_ready_flag   = true;}

// --- helper: set duty (0.0–1.0) ---
void setLaser(int channel, float duty) {
  // channel mapping:
  // 0: pin24 (SM0A)
  // 1: pin25 (SM0B)
  // 2: pin5  (SM2A)
  // 3: pin4  (SM2B)
  int sm = (channel < 2) ? 0 : 2;
  bool isB = (channel == 1 || channel == 3);
  auto &S = FLEXPWM2.SM[sm];
  uint16_t val = (uint16_t)(duty * (MOD + 1));
  if (isB) {
    S.VAL4 = 0;
    S.VAL5 = val;
  } else {
    S.VAL2 = 0;
    S.VAL3 = val;
  }
  FLEXPWM2_MCTRL |= FLEXPWM_MCTRL_LDOK(1 << sm);  // load safely
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
    Serial.print("entering z-stack mode, nZ: ");
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
    z_stacking  = false;
    scanning  = true;
  
  } else if (word == "delay") {
    Serial.println("setting cam trigger delay");
    cam_delay   = values[0];
  
  } else if (word == "filter") {
    Serial.println("waiting for filter movement");
    filter_ready_flag = false;

  } else if (word == "stop") {
    Serial.println("stopping");
    z_stacking  = false;
    scanning    = false;
    set_galvo(park);
  
  } else if (word == "405") {
    Serial.print("405 laser: ");Serial.println(values[0]);
    setLaser(0,values[0]/100);

  } else if (word == "488") {
    Serial.print("488 laser: ");Serial.println(values[0]);
    setLaser(1,values[0]/100);

  } else if (word == "520") {
    Serial.print("520 laser: ");Serial.println(values[0]);
    setLaser(2,values[0]/100);

  } else if (word == "640") {
    Serial.print("640 laser: ");Serial.println(values[0]);
    setLaser(3,values[0]/100);
  }  

  } else if (word == "galvo") {
    Serial.print("galvo to ");Serial.println(values[0]);
    z_stacking  = false;
    scanning    = false;
    set_galvo(values[0]);

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
  
  digitalWriteFast(CamOut,LOW);
  //SCAN
  for(int g=0;g<1024;g++){
    if(g==cam_trigger_step)     {digitalWriteFast(CamOut, HIGH); camera_ready_flag = false; }  // trigger camera 9 * line interval (us) before beam enters FOV
    
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(g);

  }
  digitalWriteFast(CamOut, LOW);

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