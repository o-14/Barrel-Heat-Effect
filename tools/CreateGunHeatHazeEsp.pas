unit UserScript;

const
  TargetPluginName = 'GunHeatHaze.esp';
  QuestEditorID = 'GunHeatControllerQuest';
  QuestFullName = 'Gun Heat Haze Controller';
  ControllerScriptName = 'GunHeat:GunHeatController';

function FindRecordByEdid(f: IInterface; signature, edid: string): IInterface;
var
  group: IInterface;
begin
  Result := nil;
  group := GroupBySignature(f, signature);
  if Assigned(group) then
    Result := MainRecordByEditorID(group, edid);
end;

function EnsureScript(q: IInterface): Boolean;
var
  vmad: IInterface;
  scripts: IInterface;
  script: IInterface;
begin
  Result := False;

  Add(q, 'VMAD', True);
  vmad := ElementBySignature(q, 'VMAD');
  if not Assigned(vmad) then begin
    AddMessage('ERROR: Could not create VMAD on ' + Name(q));
    Exit;
  end;

  SetElementNativeValues(vmad, 'Version', 6);

  scripts := ElementByPath(vmad, 'Scripts');
  if not Assigned(scripts) then begin
    Add(vmad, 'Scripts', True);
    scripts := ElementByPath(vmad, 'Scripts');
  end;

  if not Assigned(scripts) then begin
    AddMessage('ERROR: Could not create VMAD Scripts array.');
    Exit;
  end;

  script := ElementByIndex(scripts, 0);
  if not Assigned(script) then
    script := ElementAssign(scripts, HighInteger, nil, False);

  if not Assigned(script) then begin
    AddMessage('ERROR: Could not create VMAD Script entry.');
    Exit;
  end;

  SetElementEditValues(script, 'scriptName', ControllerScriptName);
  SetElementNativeValues(script, 'Flags', 0);
  Result := True;
end;

function Initialize: Integer;
var
  masterFile: IInterface;
  targetFile: IInterface;
  questGroup: IInterface;
  quest: IInterface;
begin
  Result := 0;
  AddMessage('=== Creating Gun Heat Haze ESP ===');

  masterFile := FileByName('Fallout4.esm');
  if not Assigned(masterFile) then begin
    AddMessage('ERROR: Fallout4.esm is not loaded.');
    Exit;
  end;

  targetFile := FileByName(TargetPluginName);
  if not Assigned(targetFile) then begin
    targetFile := AddNewFileName(TargetPluginName);
    if not Assigned(targetFile) then begin
      AddMessage('ERROR: Could not create ' + TargetPluginName + '.');
      Exit;
    end;
  end;

  AddMasterIfMissing(targetFile, 'Fallout4.esm');

  quest := FindRecordByEdid(targetFile, 'QUST', QuestEditorID);
  if not Assigned(quest) then begin
    questGroup := GroupBySignature(targetFile, 'QUST');
    if not Assigned(questGroup) then
      questGroup := Add(targetFile, 'QUST', True);

    if Assigned(questGroup) then
      quest := Add(questGroup, 'QUST', True);
  end;

  if not Assigned(quest) then begin
    AddMessage('ERROR: Could not create quest record.');
    Exit;
  end;

  SetElementEditValues(quest, 'EDID', QuestEditorID);
  SetElementEditValues(quest, 'FULL', QuestFullName);
  Add(quest, 'DNAM', True);
  SetElementNativeValues(quest, 'DNAM\Flags', 1);
  SetElementNativeValues(quest, 'DNAM\Priority', 0);

  if not EnsureScript(quest) then
    Exit;

  CleanMasters(targetFile);

  AddMessage('Created/updated: ' + Name(quest));
  AddMessage('Attached script: ' + ControllerScriptName);
  AddMessage('Save ' + TargetPluginName + ' when closing FO4Edit.');
  AddMessage('=== Gun Heat Haze ESP complete ===');
end;

end.
