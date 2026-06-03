# IEEE14 Mask/Pretrain Ablation

Mode: `smoke`

This table is a paper-method ablation scaffold. It excludes oracle BC and safe gate.
Variant D is the paper proposed combination: do-nothing pretrain + invalid action mask.

- A_no_pretrain_no_mask: mean negative return `88.1911`
- B_no_pretrain_mask: mean negative return `88.1911`
- C_pretrain_no_mask: mean negative return `88.1911`
- D_pretrain_mask_proposed: mean negative return `88.1911`
