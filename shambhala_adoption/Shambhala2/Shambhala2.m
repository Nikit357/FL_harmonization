fileID = fopen('args.txt','r');
sizeA = [3 1];
A = fscanf(fileID,'%f',sizeA);
fclose(fileID);
    
NH = A(1);
NP = A(2);
k = A(3);
 
inData=readExpressionData("P_prim.txt",'log2');   
Exp = inData.Samples;
SYMBOL = inData.GeneList;
SN = inData.SamplesName;
NS = length(SN);
    
for ( i = 1:NH ) 
    message = sprintf('Harmonizing sample %d out of %d',i,NH);
    disp(message);
        
    i0 = i;
    for ( jjj = 1:NP )             
        i0 = [i0 (jjj+NH)];
    end   
        
    EXP = Exp(:,i0);
    EXP = quantilenorm(EXP);
        
    dataN = CuBlock(real(EXP),[],k);

    log2e = log2(exp(1));
    DataN = dataN/log2e;

    EXPN = exp(DataN)-1;
    vecN = EXPN(:,1);
        
    if ( i == 1 ) 
        OUT = vecN;
    else    
        OUT = [OUT vecN];
    end

end

outFileName = 'Cu_bis.txt'; 
outFile=fopen(outFileName,'w');
nG=size(OUT,1);
nS=size(OUT,2);
for i=1:nG
    fprintf(outFile,'%s',SYMBOL{i,1});        
    for j=1:nS
        fprintf(outFile,' %f',OUT(i,j));        
    end
    fprintf(outFile, '\n');
end
fclose(outFile);
    

