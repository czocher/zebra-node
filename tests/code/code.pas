program HelloWorld;
var j,a,b : integer;
begin
	read(a);
	read(b);
	for  j:= 1 to b do
	begin
		if (j>=a) then
		begin
			write(j);
			write(' ');
		end;
	end;
	writeln();
end.
