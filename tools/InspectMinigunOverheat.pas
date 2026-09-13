unit UserScript;

var
  OutputLines: TStringList;

procedure LogLine(s: string);
begin
  OutputLines.Add(s);
end;

function ContainsAny(haystack: string): Boolean;
var
  s: string;
begin
  s := LowerCase(haystack);
  Result :=
    (Pos('minigun', s) > 0) or
    (Pos('overheat', s) > 0) or
    (Pos('gunlgoverheatmpslight', s) > 0) or
    (Pos('mirage', s) > 0) or
    (Pos('refraction', s) > 0) or
    (Pos('distort', s) > 0) or
    (Pos('heat', s) > 0) or
    (Pos('mpslight', s) > 0);
end;

procedure DumpElement(e: IInterface; indent: string; depth: Integer);
var
  i: Integer;
  child: IInterface;
  line: string;
begin
  if not Assigned(e) then
    Exit;

  line := indent + Name(e) + ' | Path=' + Path(e) + ' | Value=' + GetEditValue(e);
  if (depth = 0) or ContainsAny(line) then
    LogLine(line);

  if depth <= 0 then
    Exit;

  for i := 0 to ElementCount(e) - 1 do begin
    child := ElementByIndex(e, i);
    DumpElement(child, indent + '  ', depth - 1);
  end;
end;

procedure InspectGroup(masterFile: IInterface; signature: string; depth: Integer);
var
  groupRecord: IInterface;
  rec: IInterface;
  i: Integer;
  recText: string;
begin
  groupRecord := GroupBySignature(masterFile, signature);
  if not Assigned(groupRecord) then
    Exit;

  for i := 0 to ElementCount(groupRecord) - 1 do begin
    rec := ElementByIndex(groupRecord, i);
    recText := EditorID(rec) + ' ' + Name(rec);
    if ContainsAny(recText) then begin
      LogLine('');
      LogLine('=== ' + signature + ': ' + Name(rec) + ' ===');
      DumpElement(rec, '', depth);
    end;
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
    OutputLines.SaveToFile(
      'minigun-overheat-records.txt'
    );
    OutputLines.Free;
    Exit;
  end;

  InspectGroup(masterFile, 'WEAP', 8);
  InspectGroup(masterFile, 'OMOD', 8);
  InspectGroup(masterFile, 'ARTO', 8);
  InspectGroup(masterFile, 'EFSH', 8);
  InspectGroup(masterFile, 'MATO', 8);
  InspectGroup(masterFile, 'MSWP', 8);
  InspectGroup(masterFile, 'STAT', 6);
  InspectGroup(masterFile, 'MSTT', 6);
  InspectGroup(masterFile, 'LIGH', 6);
  InspectGroup(masterFile, 'FLST', 6);
  InspectGroup(masterFile, 'KYWD', 4);

  OutputLines.SaveToFile(
    'minigun-overheat-records.txt'
  );
  OutputLines.Free;
end;

end.
