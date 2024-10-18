#include <SPI.h>

//galvos
const byte CS    = 12; 
const byte CLOCK = 13;
const byte DATA  = 11;
//stage
const byte Xo  = 31;
const byte Yo  = 29;
const byte Zo  = 27;
const byte Xi  = 32;
const byte Yi  = 30;
const byte Zi  = 28;
volatile bool x_stage_flag = false; //flags for tracking when stage moves are complete
volatile bool y_stage_flag = false;
volatile bool z_stage_flag = false;

//digital I/O
const byte CamOut  = 23;
const byte CamIn   = 22;
const byte trigger_LED     = 16;
const byte trigger_Filter  = 40;
const byte trigger_Laser   = 35;
const byte IOf  = 33;
volatile bool cam_ready = true;
const float firmware = 1.0;



const byte HALF_CLOCK_PERIOD = 1; //2 uS of clock period 

void setup() {
  Serial.begin(115200);
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
  attachInterrupt(digitalPinToInterrupt(Xi), x_move_complete, FALLING);
  attachInterrupt(digitalPinToInterrupt(Yi), y_move_complete, FALLING);
  attachInterrupt(digitalPinToInterrupt(Zi), z_move_complete, FALLING);
  
  pinMode(CamIn, INPUT);
  attachInterrupt(digitalPinToInterrupt(CamIn), camera_ready, RISING);

  pinMode(CamOut, OUTPUT);
  digitalWrite(CamOut, LOW);
  
}

void x_move_complete(){x_stage_flag = true;}
void y_move_complete(){y_stage_flag = true;}
void z_move_complete(){z_stage_flag = true;}

uint32_t prev_scan = 0; // previous scan time
uint32_t Scan = 0;      // store exposure time (µs), 0 for no scan

void camera_ready(){cam_ready = true;}

void loop() {
checkSerial();
if(Scan > 0){
  if(micros() > prev_scan + Scan){

    sweep(Scan);
    }
  }
}

//~~~~~~~~~~~~~~~~~~~~~~~~~~ Serial communications ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
String device = "";
String command1 = "";
String command2 = "";
String command3 = "";
String command4 = "";
String command5 = "";
String echo = "";

int serial_part = 0;
bool verbose = true;

void checkSerial(){
  char rc;
  while (Serial.available()) {
   rc = Serial.read();
   if (rc == 47)      {serial_part = 1; device = "";command1 = "";command2 = ""; echo="/";}           // '/' char
   else if (rc == 46)      {serial_part += 1; echo+=rc;}                                              // '.' char
   else if (rc == 59)      {
                            serial_part = 0; echo+="; --> ";
                            if(verbose){Serial.print(echo);}
                            respond(device,command1,command2,command3,command4,command5);   // ';' char
                            }   
   else if (serial_part == 1){device   += rc; echo+=rc;}
   else if (serial_part == 2){command1 += rc; echo+=rc;}
   else if (serial_part == 3){command2 += rc; echo+=rc;}
   else if (serial_part == 4){command3 += rc; echo+=rc;}
   else if (serial_part == 5){command4 += rc; echo+=rc;}
   else if (serial_part == 6){command5 += rc; echo+=rc;}
 }
}





void respond(String device,String command1, String command2, String command3, String command4, String command5) {
//z-stack
    if(device == "Stack")               {z_stack(command1.toInt(),command2.toInt(),command3.toInt());}
//test functions    
    if(device == "C")                   {trigger_camera();}             // Camera trigger
    if(device == "G")                   {set_galvo(command1.toInt());   if(verbose){Serial.print("Galvo: ");Serial.println(command1.toInt());}}  // Galvo command
    if(device == "X")                   {increment_stage(0);            if(verbose){Serial.println("Increment X");}}           // Stage command
    if(device == "Y")                   {increment_stage(1);            if(verbose){Serial.println("Increment Y");}}           // Stage command
    if(device == "Z")                   {increment_stage(2);            if(verbose){Serial.println("Increment Z");}}           // Stage command
    if(device == "S")                   {sweep(command1.toInt());       if(verbose){Serial.print("Sweep: ");Serial.println(command1.toInt());}}  // Single sweep galvos - transit time in milliseconds
    if(device == "Scan")                {Scan = command1.toInt()*1000;  
                                          if(command1.toInt()==0){set_galvo(511);} //when stopping scan, return mirror to centre
                                          if(verbose){Serial.print("Scan: ");Serial.println(command1.toInt());}} // Repeatedly sweep galvos - 0 to turn off (ms)
    
//handshake    
    if(device == "hello")               {Serial.println("Dual Illumination Lightsheet");}

    if(device == "firmware")            {Serial.println(firmware);}
}

void trigger_camera(){
  digitalWrite(CamOut,1);
  delayMicroseconds(1000);
  digitalWrite(CamOut,0);
}

           //number of z, z step size, exposure time
void z_stack(uint16_t nZ, uint32_t sZ, uint32_t E){
  //initially set scanner to 0
  set_galvo(0);
  delay(2);
  for(int z=0;z<nZ;z++){
    //trigger galvo sweep and camera
    sweep(E);
    set_galvo(0); //return scanner to start ready for next image
  //move Z
    increment_stage(2);
  //confirm move
    //while(z_stage_flag==false){}
  }
  //respond to PC
}

long unsigned int t0 = 0;

void sweep(uint32_t exposure){ //input exposure time in microSeconds
  //calculate step time
  float s_t = exposure/1000.0;//s_t: 10-bit DAC, spread over 1000/1024 of the DAC range

  uint32_t prev_micros = 0;
  int s= 1; //n DAC steps to move each time
// step times <2µs can't be written to the DAC fast enough, need to increase step time and decrease DAC resolution
  if(s_t < 2.0 and s_t >=1.0)     {s_t = s_t * 2.0; s=2;  }
  if(s_t < 1.0)                   {s_t = s_t * 4.0; s=4;  }
  uint32_t s_t_int = int(s_t);

  digitalWriteFast(CamOut, HIGH); // start camera exposure
  delayMicroseconds(87);
  for(int i=0;i<1024;i=i+s){
    while(micros() < prev_micros + s_t_int){} //delay for step time
    prev_micros = micros();
    set_galvo(i);
  }
  digitalWriteFast(CamOut,LOW);
}

void increment_stage(int axis){
  if(axis==2){
    z_stage_flag = false;
    digitalWrite(Zo,0);
    delayMicroseconds(1000);
    digitalWrite(Zo,1);
  }
  if(axis==1){
    y_stage_flag = false;
    digitalWrite(Yo,0);
    delayMicroseconds(1000);
    digitalWrite(Yo,1);
  }
  if(axis==0){
    x_stage_flag = false;
    digitalWrite(Xo,0);
    delayMicroseconds(1000);
    digitalWrite(Xo,1);
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