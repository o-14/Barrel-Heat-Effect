unit UserScript;

const
  PatchFileName = 'GunHeatHaze.esp';
  SourceProjectileFormID = $0003ADFB; // MiniGunProjectile
  HazeMuzzleModel = 'Effects\SaugusSmokeMirage.nif';
  MuzzleDurationSeconds = '0.250000';

function RequireElement(container: IInterface; path: string): IInterface;
begin
  Result := ElementByPath(container, path);
  if not Assigned(Result) then
    raise Exception.Create('Missing element path: ' + path + ' on ' + Name(container));
end;

function Initialize: Integer;
var
  masterFile: IInterface;
  patchFile: IInterface;
  sourceProjectile: IInterface;
  overrideProjectile: IInterface;
begin
  Result := 0;

  masterFile := FileByName('Fallout4.esm');
  if not Assigned(masterFile) then
    raise Exception.Create('Fallout4.esm is not loaded.');

  patchFile := FileByName(PatchFileName);
  if not Assigned(patchFile) then begin
    AddMessage('Creating ' + PatchFileName);
    patchFile := AddNewFileName(PatchFileName);
  end else
    AddMessage('Updating ' + PatchFileName);

  AddMasterIfMissing(patchFile, 'Fallout4.esm', True);

  sourceProjectile := RecordByFormID(masterFile, SourceProjectileFormID, True);
  if not Assigned(sourceProjectile) then
    raise Exception.Create('MiniGunProjectile [0003ADFB] was not found in Fallout4.esm.');

  overrideProjectile := wbCopyElementToFile(sourceProjectile, patchFile, False, True);
  if not Assigned(overrideProjectile) then
    raise Exception.Create('Could not copy MiniGunProjectile as an override.');

  SetEditValue(
    RequireElement(overrideProjectile, 'Muzzle Flash Model\NAM1'),
    HazeMuzzleModel
  );

  SetEditValue(
    RequireElement(overrideProjectile, 'DNAM\Muzzle Flash - Duration'),
    MuzzleDurationSeconds
  );

  CleanMasters(patchFile);

  AddMessage('GunHeatHaze method 1 patch complete.');
  AddMessage('  MiniGunProjectile muzzle model: ' + HazeMuzzleModel);
  AddMessage('  Muzzle flash duration: ' + MuzzleDurationSeconds + ' seconds');
  AddMessage('Close xEdit and save ' + PatchFileName + ' when prompted if -autoexit does not save automatically.');
end;

end.
