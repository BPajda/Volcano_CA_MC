; PottsMC::unlikeBeforeAfter wstawione w sweepTrials<0,0> po etapie 8 (k1): cl /O2 /Ob2 /DNDEBUG /FAs (MSVC 19.38).
; Pętla po sąsiadach $LL25: liczniki przez setne/sete, jedyny skok to powrót pętli (jb) — porównaj PottsMC_sweep_msvc_O2.asm (przed: je po porównaniu).
	test	r15, r15
	je	SHORT $LN24@sweepTrial
	npad	5
$LL25@sweepTrial:
; 148  :             const std::int32_t sj = spinAtCell[offsets[k]];
	mov	rcx, QWORD PTR [r13+r8*8]
; 149  :             inDomain += static_cast<int>(sj != 0);
	xor	eax, eax
	add	rcx, rbx
	mov	edx, DWORD PTR [r14+rcx*4]
	test	edx, edx
	setne	al
	add	r9d, eax
; 150  :             sameA += static_cast<int>(sj == a);
	xor	eax, eax
	cmp	edx, r12d
	sete	al
	add	r10d, eax
; 151  :             sameB += static_cast<int>(sj == b);
	xor	eax, eax
	cmp	edx, ebp
	sete	al
