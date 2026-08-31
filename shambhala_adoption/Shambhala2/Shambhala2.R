library(matrixStats)

# k (OPTIONAL) is the number of probe clusters for the application of k-means to find probe-cluster partitions. By default it is 5.

Shambhala2 <- function(InputFileName, PFileName, QFileName, delete_buffer_files = TRUE, k = 5) {

    cat("\n======================================================\n")
    cat("🪲 STARTING SHAMBHALA2 DIAGNOSTIC RUN\n")
    cat("======================================================\n\n")

    IFN = InputFileName
    MAS = read.table(IFN, header = TRUE, sep = ",")
    cat("1. 📥 INPUT DATA (", IFN, "):\n")
    cat("   - Rows:", nrow(MAS), " Cols:", ncol(MAS), "\n")
    
    MAS0 = as.matrix(MAS[,-1])
    NS = ncol(MAS0)
    SYMBOL = as.vector(MAS[,1])
    CN = colnames(MAS)
    cat("   - NS (Number of Input Samples):", NS, "\n\n")

    PFN = PFileName 
    P = read.table(PFN, header = TRUE, sep = ",")
    cat("2. 📥 P REFERENCE (", PFN, "):\n")
    cat("   - Rows:", nrow(P), " Cols:", ncol(P), "\n\n")
   
    pool = merge(MAS,P,by = "SYMBOL")
    cat("3. 🔄 POOL AFTER MERGE (MAS + P):\n")
    cat("   - Rows:", nrow(pool), " Cols:", ncol(pool), "\n\n")

    NS1 = ncol(pool)
    NG1 = nrow(pool)

    for ( j in (NS+2):NS1 ) {
        pool[,j] = as.numeric(pool[,j])
    }     
   
    P1FN = "P_prim.txt"
    write.table(pool, P1FN, row.names = FALSE, col.names = TRUE, sep = "\t")

    NH = ncol(MAS) - 1
    NP = ncol(P) - 1

    args = c(NH,NP,k)
    
    AFN = "args.txt"
    write.table(args, AFN, row.names = FALSE, col.names = FALSE)

    octave_cmd = "/opt/conda/bin/octave --no-gui --eval \"source('Shambhala2.m');\" > octave_debug.log 2>&1"
    
    cat("4. 🚀 EXECUTING OCTAVE ENGINE...\n")
    system(octave_cmd)

    Cu2FN = "Cu_bis.txt"
    
    if (!file.exists(Cu2FN)) {
        stop("🛑 OCTAVE EXECUTION FAILED! Cu_bis.txt was not generated.")
    }

    # Reading Octave Output
    MAS_out = read.table(Cu2FN, header = FALSE)
    cat("5. 📥 OCTAVE OUTPUT (Cu_bis.txt):\n")
    cat("   - Rows:", nrow(MAS_out), " Cols:", ncol(MAS_out), "\n")
    
    # Check if Octave output squashed everything into 1 column
    if(ncol(MAS_out) < 2) {
        cat("   - ⚠️ WARNING: Octave output has only 1 column! Here is row 1:\n")
        print(head(MAS_out, 1))
    }
    cat("\n")

    MAS_out = as.matrix(MAS_out)

    Q = read.table(QFileName, header = TRUE, sep = ",")
    cat("6. 📥 Q REFERENCE (", QFileName, "):\n")
    cat("   - Rows:", nrow(Q), " Cols:", ncol(Q), "\n\n")

    MAS1 = merge(MAS_out, Q, by = 1)
    cat("7. 🔄 MAS1 AFTER MERGE (Octave Output + Q):\n")
    cat("   - Rows:", nrow(MAS1), " Cols:", ncol(MAS1), "\n\n")

    NS1 = ncol(MAS1)

    for ( j in 2:NS1 ) {
        MAS1[,j] = as.numeric(MAS1[,j])
    } 

    cat("8. ✂️ SUBSETTING MAS3 (The crash point):\n")
    cat("   - Target Start Column (NS + 2):", (NS + 2), "\n")
    cat("   - Target End Column (ncol(MAS1)):", ncol(MAS1), "\n")
    
    if ((NS + 2) > ncol(MAS1)) {
        cat("\n💥 FATAL ERROR CAUGHT: Cannot subset columns from", (NS + 2), "to", ncol(MAS1), "because MAS1 is too small!\n")
        stop("Script halted to prevent 'undefined columns selected' error.")
    }

    MAS3 = MAS1[,(NS+2):ncol(MAS1)]

    RM = rowMeans(log(as.matrix(MAS3)))
    RS = rowSds(log(as.matrix(MAS3))) 

    MAS2 = MAS1[,2:(NS+1)]

    MAS22 = log(MAS2+1)

    NR = nrow(MAS22)
 
    for ( nr in 1:NR ) {
        MAS22[nr,] = RM[nr] + RS[nr]*MAS22[nr,]
    }

    MAS23 = exp(MAS22)

    SYMBOL = as.vector(MAS1[,1])

    MAS33 = cbind(SYMBOL,MAS23)

    for ( j in 2:(NS+1) ) {
        MAS33[,j] = as.vector(as.numeric(MAS33[,j]))
    } 

    if ( delete_buffer_files ) {
        if (file.exists(P1FN)) file.remove(P1FN) 
        if (file.exists(Cu2FN)) file.remove(Cu2FN) 
        if (file.exists(AFN)) file.remove(AFN) 
    }
    
    colnames(MAS33) = CN
    cat("\n✅ HARMONIZATION COMPLETE!\n")
    return(MAS33)
}

Harmonized = Shambhala2("comb_exp_log_dedup.csv", "P0.csv", "Q0.csv", delete_buffer_files = TRUE, k = 5) 

OFN = "shambhala_harmonized.csv"

#Harmonized = Shambhala2("Input.csv", "P0.csv", "Q0.csv", delete_buffer_files = TRUE, k = 5) 

#OFN = "Output.csv"

write.table(Harmonized, OFN, col.names = TRUE, row.names = FALSE, sep =",")



Shambhala2_flex <- function(InputDataFrame, PFileName, QFileName, delete_buffer_files = TRUE, k = 5) {

    # 1. Directly use the provided DataFrame instead of reading from a file
    MAS = as.data.frame(InputDataFrame)
    MAS0 = as.matrix(MAS[,-1])
    NS = ncol(MAS0)
    SYMBOL = as.vector(MAS[,1])
    CN = colnames(MAS)

    PFN = PFileName 
    P = read.table(PFN, header = TRUE, sep = ",")
   
    pool = merge(MAS,P,by = "SYMBOL")

    NS1 = ncol(pool)
    NG1 = nrow(pool)

    for ( j in (NS+2):NS1 ) {
        pool[,j] = as.numeric(pool[,j])
    }     
   
    P1FN = "P_prim.txt"
    write.table(pool, P1FN, row.names = FALSE, col.names = TRUE, sep = "\t")

    NH = ncol(MAS) - 1
    NP = ncol(P) - 1

    args = c(NH,NP,k)
    
    AFN = "args.txt"
    write.table(args, AFN, row.names = FALSE, col.names = FALSE)

    octave_cmd = "/opt/conda/bin/octave --no-gui --eval \"source('Shambhala2.m');\" > octave_debug.log 2>&1"
    
    print(paste("Executing Octave command:", octave_cmd))
    system(octave_cmd)

    Cu2FN = "Cu_bis.txt"
    
    # 3. Fail-safe check: If Octave crashed, Cu_bis.txt won't exist.
    # Stop R immediately and point to the log file.
    if (!file.exists(Cu2FN)) {
        stop("🛑 OCTAVE EXECUTION FAILED! Cu_bis.txt was not generated. Please open 'octave_debug.log' to see the exact Octave error.")
    }

    # Rename the incoming octave matrix to MAS_out to avoid confusion
    MAS_out = read.table(Cu2FN, header = FALSE, sep = " ")
    MAS_out = as.matrix(MAS_out)

    # BUGFIX: The reading of QFileName was missing in your original snippet!
    Q = read.table(QFileName, header = TRUE, sep = ",")

    MAS1 = merge(MAS_out, Q, by = 1)

    NS1 = ncol(MAS1)

    for ( j in 2:NS1 ) {
        MAS1[,j] = as.numeric(MAS1[,j])
    } 

    MAS3 = MAS1[,(NS+2):ncol(MAS1)]

    RM = rowMeans(log(as.matrix(MAS3)))
    RS = rowSds(log(as.matrix(MAS3))) 

    MAS2 = MAS1[,2:(NS+1)]

    MAS22 = log(MAS2+1)

    NR = nrow(MAS22)
 
    for ( nr in 1:NR ) {
        MAS22[nr,] = RM[nr] + RS[nr]*MAS22[nr,]
    }

    MAS23 = exp(MAS22)

    SYMBOL_out = as.vector(MAS1[,1])

    MAS33 = cbind(SYMBOL_out, MAS23)

    for ( j in 2:(NS+1) ) {
        MAS33[,j] = as.vector(as.numeric(MAS33[,j]))
    } 

    if ( delete_buffer_files ) {

        if (file.exists(P1FN)) {
            file.remove(P1FN) 
        }
    
        if (file.exists(Cu2FN)) {
            file.remove(Cu2FN) 
        }
  
        if (file.exists(AFN)) {
            file.remove(AFN) 
        }

    }
    
    colnames(MAS33) = CN
    
    return(MAS33)
    
}
   
