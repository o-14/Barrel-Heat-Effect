unit UserScript;

var
  OutputLines: TStringList;

procedure LogLine(s: string);
begin
  OutputLines.Add(s);
end;

function HasNeedle(haystack: string): Boolean;
var
  s: string;
begin
  s := LowerCase(haystack);
  Result :=
    (Pos('muzzle', s) > 0) or
    (Pos('muz', s) > 0) or
    (Pos('flash', s) > 0) or
    (Pos('fire', s) > 0) or
    (Pos('heat', s) > 0) or
    (Pos('overheat', s) > 0);
end;

procedure DumpElement(e: IInterface; indent: string; depth: Integer);
var
  i: Integer;
  child: IInterface;
begin
  if not Assigned(e) then
    Exit;

  LogLine(indent + Name(e) + ' | Path=' + Path(e) + ' | Value=' + GetEditValue(e));

  if depth <= 0 then
    Exit;

  for i := 0 to ElementCount(e) - 1 do begin
    child := ElementByIndex(e, i);
    DumpElement(child, indent + '  ', depth - 1);
  end;
end;

procedure DumpRecord(rec: IInterface; depth: Integer);
begin
  if not Assigned(rec) then
    Exit;

  LogLine('');
  LogLine('=== ' + Signature(rec) + ': ' + Name(rec) + ' ===');
  DumpElement(rec, '', depth);
end;

procedure DumpEditorID(masterFile: IInterface; signature: string; edid: string; depth: Integer);
var
  rec: IInterface;
begin
  rec := MainRecordByEditorID(GroupBySignature(masterFile, signature), edid);
  if Assigned(rec) then
    DumpRecord(rec, depth)
  else
    LogLine('MISSING ' + signature + ' ' + edid);
end;

procedure DumpMatchingGroup(masterFile: IInterface; signature: string; depth: Integer);
var
  groupRecord: IInterface;
  rec: IInterface;
  edid: string;
  i: Integer;
begin
  groupRecord := GroupBySignature(masterFile, signature);
  if not Assigned(groupRecord) then
    Exit;

  for i := 0 to ElementCount(groupRecord) - 1 do begin
    rec := ElementByIndex(groupRecord, i);
    edid := EditorID(rec);
    if HasNeedle(edid + ' ' + Name(rec)) then
      DumpRecord(rec, depth);
  end;
end;

function Initialize: Integer;
var
  masterFile: IInterface;
begin
  Result := 0;
  OutputLines := TStringList.Create;
  masterFile := FileByName('Fallout4.esm');

  if not Assigned(masterFile) then begin
    OutputLines.Add('ERROR: Fallout4.esm is not loaded.');
    OutputLines.SaveToFile('muzzle-patch-targets.txt');
    OutputLines.Free;
    Exit;
  end;

  DumpEditorID(masterFile, 'WEAP', '10mm', 10);
  DumpEditorID(masterFile, 'WEAP', 'AssaultRifle', 10);
  DumpEditorID(masterFile, 'WEAP', 'Minigun', 10);
  DumpEditorID(masterFile, 'WEAP', 'PipeGun', 10);
  DumpEditorID(masterFile, 'WEAP', 'HuntingRifle', 10);
  DumpEditorID(masterFile, 'WEAP', 'DoubleBarrelShotgun', 10);

  LogLine('');
  LogLine('### Muzzle-ish OMOD records ###');
  DumpMatchingGroup(masterFile, 'OMOD', 9);

  LogLine('');
  LogLine('### Muzzle-ish ARTO records ###');
  DumpMatchingGroup(masterFile, 'ARTO', 8);

  LogLine('');
  LogLine('### Muzzle-ish EFSH records ###');
  DumpMatchingGroup(masterFile, 'EFSH', 8);

  OutputLines.SaveToFile('muzzle-patch-targets.txt');
  OutputLines.Free;
end;

end.
