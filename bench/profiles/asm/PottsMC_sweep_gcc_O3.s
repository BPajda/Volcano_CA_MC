_ZN7volcano7PottsMC5sweepEv:
.LFB3232:
	.cfi_startproc
	endbr64
	pushq	%r15
	.cfi_def_cfa_offset 16
	.cfi_offset 15, -16
	pushq	%r14
	.cfi_def_cfa_offset 24
	.cfi_offset 14, -24
	pushq	%r13
	.cfi_def_cfa_offset 32
	.cfi_offset 13, -32
	pushq	%r12
	.cfi_def_cfa_offset 40
	.cfi_offset 12, -40
	pushq	%rbp
	.cfi_def_cfa_offset 48
	.cfi_offset 6, -48
	pushq	%rbx
	.cfi_def_cfa_offset 56
	.cfi_offset 3, -56
	movq	%rdi, %rbx
	subq	$72, %rsp
	.cfi_def_cfa_offset 128
	movq	200(%rbx), %rcx
	movq	208(%rbx), %rdx
	movslq	248(%rdi), %rdi
	movq	152(%rbx), %r14
	subq	%rcx, %rdx
	movq	%rcx, 16(%rsp)
	movl	24(%rbx), %ecx
	subl	$1, %ecx
	sarq	$3, %rdx
	movslq	%ecx, %rcx
	movq	%rdx, (%rsp)
	movq	%rcx, 32(%rsp)
	movq	160(%rbx), %rcx
	movq	%rcx, 24(%rsp)
	je	.L186
	movabsq	$-7046029254386353131, %r12
	xorl	%r13d, %r13d
	movabsq	$-6884282663029611473, %rdx
	xorq	16(%rbx), %rdx
	movabsq	$-4658895280553007687, %rsi
	addq	%r12, %rdx
	movabsq	$-7723592293110705685, %rcx
	movq	$0, 40(%rsp)
	movq	%rdx, %rax
	shrq	$30, %rax
	xorq	%rdx, %rax
	imulq	%rsi, %rax
	movq	%rax, %rdx
	shrq	$27, %rdx
	xorq	%rax, %rdx
	imulq	%rcx, %rdx
	movq	%rdx, %rax
	xorq	%rdx, %rdi
	shrq	$31, %rax
	xorq	%rdi, %rax
	addq	%r12, %rax
	movq	%rax, %rdx
	shrq	$30, %rdx
	xorq	%rax, %rdx
	imulq	%rsi, %rdx
	movq	%rdx, %rax
	shrq	$27, %rax
	xorq	%rdx, %rax
	imulq	%rcx, %rax
	movq	%rax, %rdx
	shrq	$31, %rdx
	xorq	%rax, %rdx
	movq	%rdx, 8(%rsp)
	jmp	.L185
	.p2align 4,,10
	.p2align 3
.L171:
	addq	$1, %r13
	cmpq	%r13, (%rsp)
	je	.L203
.L185:
	movabsq	$-4658895280553007687, %rsi
	movq	8(%rsp), %rax
	movabsq	$-7723592293110705685, %rcx
	xorq	%r13, %rax
	addq	%r12, %rax
	movq	%rax, %rdx
	shrq	$30, %rdx
	xorq	%rax, %rdx
	imulq	%rsi, %rdx
	movq	%rdx, %rax
	shrq	$27, %rax
	xorq	%rdx, %rax
	movabsq	$5567381839951905605, %rdx
	imulq	%rcx, %rax
	movq	%rax, %rdi
	shrq	$31, %rdi
	xorq	%rax, %rdi
	xorq	%rdi, %rdx
	addq	%r12, %rdx
	movq	%rdx, %rax
	shrq	$30, %rax
	xorq	%rdx, %rax
	imulq	%rsi, %rax
	movq	%rax, %rdx
	shrq	$27, %rdx
	xorq	%rax, %rdx
	imulq	%rcx, %rdx
	movq	%rdx, %rax
	shrq	$31, %rax
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	(%rsp)
	movq	16(%rsp), %rax
	movq	(%rax,%rdx,8), %rbp
	leaq	0(,%rbp,4), %r15
	cmpq	24(%rsp), %r14
	je	.L170
	movabsq	$5567378567169920073, %r8
	pxor	%xmm0, %xmm0
	pxor	%xmm1, %xmm1
	xorq	%rdi, %r8
	cvtss2sd	(%r14,%rbp,4), %xmm1
	addq	%r12, %r8
	movq	%r8, %rax
	shrq	$30, %rax
	xorq	%r8, %rax
	imulq	%rsi, %rax
	movq	%rax, %rsi
	shrq	$27, %rsi
	xorq	%rax, %rsi
	imulq	%rcx, %rsi
	movq	%rsi, %rax
	shrq	$31, %rax
	xorq	%rsi, %rax
	shrq	$11, %rax
	cvtsi2sdq	%rax, %xmm0
	mulsd	.LC3(%rip), %xmm0
	comisd	%xmm1, %xmm0
	jnb	.L171
.L170:
	movq	224(%rbx), %rax
	movq	64(%rbx), %rsi
	subq	56(%rbx), %rsi
	addq	$1, 256(%rbx)
	movq	%rsi, %rcx
	movq	(%rax,%rdx,8), %rdx
	movabsq	$-6148914691236517205, %rax
	sarq	$3, %rcx
	imulq	%rax, %rcx
	xorl	%eax, %eax
	cmpq	$24, %rsi
	je	.L172
	movabsq	$-4658895280553007687, %rsi
	xorq	8(%rsp), %rdx
	addq	%r12, %rdx
	movq	%rdx, %rax
	shrq	$30, %rax
	xorq	%rax, %rdx
	imulq	%rsi, %rdx
	movq	%rdx, %rax
	shrq	$27, %rax
	xorq	%rax, %rdx
	movabsq	$-7723592293110705685, %rax
	imulq	%rax, %rdx
	movq	%rdx, %r8
	shrq	$31, %r8
	xorq	%r8, %rdx
	movabsq	$5639994678855225170, %r8
	xorq	%r8, %rdx
	addq	%r12, %rdx
	movq	%rdx, %r8
	shrq	$30, %r8
	xorq	%rdx, %r8
	imulq	%rsi, %r8
	movq	%r8, %rdx
	shrq	$27, %rdx
	xorq	%r8, %rdx
	imulq	%rax, %rdx
	movq	%rdx, %rax
	shrq	$31, %rax
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	%rcx
	movslq	%edx, %rdx
	leaq	(%rdx,%rdx,2), %rax
	salq	$3, %rax
.L172:
	addq	176(%rbx), %rax
	movq	104(%rbx), %r8
	movq	(%rax), %rcx
	movq	8(%rax), %rsi
	addq	%r8, %r15
	movsd	32(%rbx), %xmm0
	movl	(%r15), %r9d
	cmpq	%rsi, %rcx
	je	.L188
	movq	128(%rbx), %r11
	movq	%rcx, %rax
	xorl	%r10d, %r10d
	.p2align 4,,10
	.p2align 3
.L175:
	movq	(%rax), %rdx
	addq	%rbp, %rdx
	testb	$1, (%r11,%rdx)
	je	.L174
	cmpl	%r9d, (%r8,%rdx,4)
	setne	%dl
	movzbl	%dl, %edx
	addl	%edx, %r10d
.L174:
	addq	$8, %rax
	cmpq	%rax, %rsi
	jne	.L175
	pxor	%xmm1, %xmm1
	pxor	%xmm2, %xmm2
	cvtsi2sdl	%r10d, %xmm1
.L173:
	movabsq	$5567380779195256404, %rdx
	mulsd	%xmm0, %xmm1
	xorq	%rdi, %rdx
	addq	%r12, %rdx
	movq	%rdx, %rax
	shrq	$30, %rax
	xorq	%rdx, %rax
	movabsq	$-4658895280553007687, %rdx
	imulq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$27, %rdx
	xorq	%rax, %rdx
	movabsq	$-7723592293110705685, %rax
	imulq	%rax, %rdx
	movq	%rdx, %rax
	shrq	$31, %rax
	xorq	%rdx, %rax
	xorl	%edx, %edx
	divq	32(%rsp)
	leal	1(%rdx), %r10d
	addl	$2, %edx
	cmpl	%r10d, %r9d
	cmovle	%edx, %r10d
	cmpq	%rsi, %rcx
	je	.L189
	movq	128(%rbx), %rdx
	xorl	%r9d, %r9d
	.p2align 4,,10
	.p2align 3
.L179:
	movq	(%rcx), %rax
	addq	%rbp, %rax
	testb	$1, (%rdx,%rax)
	je	.L178
	cmpl	%r10d, (%r8,%rax,4)
	setne	%al
	movzbl	%al, %eax
	addl	%eax, %r9d
.L178:
	addq	$8, %rcx
	cmpq	%rsi, %rcx
	jne	.L179
	pxor	%xmm3, %xmm3
	cvtsi2sdl	%r9d, %xmm3
.L177:
	mulsd	%xmm3, %xmm0
	subsd	%xmm1, %xmm0
	comisd	%xmm0, %xmm2
	jnb	.L184
	movsd	40(%rbx), %xmm1
	movl	%r10d, 52(%rsp)
	comisd	%xmm2, %xmm1
	jbe	.L171
	xorpd	.LC4(%rip), %xmm0
	pxor	%xmm2, %xmm2
	movabsq	$5567365321507295316, %rax
	xorq	%rax, %rdi
	movabsq	$-4658895280553007687, %rax
	divsd	%xmm1, %xmm0
	addq	%r12, %rdi
	movq	%rdi, %rdx
	shrq	$30, %rdx
	xorq	%rdi, %rdx
	imulq	%rax, %rdx
	movq	%rdx, %rax
	shrq	$27, %rax
	xorq	%rdx, %rax
	movabsq	$-7723592293110705685, %rdx
	imulq	%rdx, %rax
	movq	%rax, %rdx
	shrq	$31, %rdx
	xorq	%rdx, %rax
	shrq	$11, %rax
	cvtsi2sdq	%rax, %xmm2
	mulsd	.LC3(%rip), %xmm2
	movsd	%xmm2, 56(%rsp)
	call	exp@PLT
	movsd	56(%rsp), %xmm2
	xorl	%eax, %eax
	movl	52(%rsp), %r10d
	comisd	%xmm2, %xmm0
	seta	%al
	addq	%rax, 272(%rbx)
	comisd	%xmm2, %xmm0
	jbe	.L171
.L184:
	movq	128(%rbx), %rax
	addq	$1, 40(%rsp)
	movl	%r10d, (%r15)
	testb	$2, (%rax,%rbp)
	je	.L171
	movq	%rbp, %rsi
	movq	%rbx, %rdi
	addq	$1, %r13
	call	_ZN7volcano7PottsMC9syncFrameEm
	cmpq	%r13, (%rsp)
	jne	.L185
	.p2align 4,,10
	.p2align 3
.L203:
	movl	248(%rbx), %eax
.L169:
	movq	40(%rsp), %rdi
	addl	$1, %eax
	addq	%rdi, 264(%rbx)
	movl	%eax, 248(%rbx)
	addq	$72, %rsp
	.cfi_remember_state
	.cfi_def_cfa_offset 56
	popq	%rbx
	.cfi_def_cfa_offset 48
	movq	%rdi, %rax
	popq	%rbp
	.cfi_def_cfa_offset 40
	popq	%r12
	.cfi_def_cfa_offset 32
	popq	%r13
	.cfi_def_cfa_offset 24
	popq	%r14
	.cfi_def_cfa_offset 16
	popq	%r15
	.cfi_def_cfa_offset 8
	ret
	.p2align 4,,10
	.p2align 3
.L188:
	.cfi_restore_state
	pxor	%xmm2, %xmm2
	movapd	%xmm2, %xmm1
	jmp	.L173
	.p2align 4,,10
	.p2align 3
.L189:
	movapd	%xmm2, %xmm3
	jmp	.L177
.L186:
	movq	$0, 40(%rsp)
	movq	%rdi, %rax
	jmp	.L169
	.cfi_endproc
.LFE3232:
	.size	_ZN7volcano7PottsMC5sweepEv, .-_ZN7volcano7PottsMC5sweepEv
