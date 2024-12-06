--lua

sim=require'sim'
simUI=require'simUI'




function handleUI(p)
    local s=sim.getObjectSel()
    if s and #s>0 and s[#s]==model then
        if not ui then
            local xml =[[<ui title="Gyro/Accel Sensor" closeable="false" placement="relative" position="50,-50" layout="form">
                    <label text="x gyro:" />
                    <label id="1" text="-" />
                    <label text="y gyro:" />
                    <label id="2" text="-" />
                    <label text="z gyro:" />
                    <label id="3" text="-" />
                    <label text="x accel:" />
                    <label id="4" text="-" />
                    <label text="y accel:" />
                    <label id="5" text="-" />
                    <label text="z accel:" />
                    <label id="6" text="-" />
            </ui>]]
            ui=simUI.create(xml)
            ui=simUI.create(xml)
        end
        if p then
            simUI.setLabelText(ui,1,string.format("%.4f",p[1]))
            simUI.setLabelText(ui,2,string.format("%.4f",p[2]))
            simUI.setLabelText(ui,3,string.format("%.4f",p[3]))
            simUI.setLabelText(ui,4,string.format("%.4f",p[4]))
            simUI.setLabelText(ui,5,string.format("%.4f",p[5]))
            simUI.setLabelText(ui,6,string.format("%.4f",p[6]))
        else
            simUI.setLabelText(ui,1,"-")
            simUI.setLabelText(ui,2,"-")
            simUI.setLabelText(ui,3,"-")
            simUI.setLabelText(ui,4,"-")
            simUI.setLabelText(ui,5,"-")
            simUI.setLabelText(ui,6,"-")
        end
    else
        if ui then
            simUI.destroy(ui)
            ui=nil
        end
    end
end

function sysCall_init() 
    model=sim.getObject('.')
    massObject=sim.getObject('./mass')
    sensor=sim.getObject('./forceSensor')
    mass=sim.getObjectFloatParam(massObject,sim.shapefloatparam_mass)
    ref=sim.getObject('./reference')
    print(ref)
end

function sysCall_sensing() 
    local gyroData=(sim.getEulerAnglesFromMatrix(sim.getObjectMatrix(ref,-1)))
    result,force=sim.readForceSensor(sensor)
    if (result>0) then
        data={gyroData[1],gyroData[3],-gyroData[2],force[1]/mass,force[3]/mass,-force[2]/mass}
        handleUI(data)
        sim.setFloatSignal('gyroX',data[1])
        sim.setFloatSignal('gyroY',data[2])
        sim.setFloatSignal('gyroZ',data[3])
        sim.setFloatSignal('accelX',data[4])
        sim.setFloatSignal('accelY',data[5])
        sim.setFloatSignal('accelZ',data[6])
    else
        handleUI(nil)
    end
end 
