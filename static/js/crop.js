const ImageCropper = (() => {
    let cropper = null;
    let croppedBlob = null;

    function showModal(file) {
        const modal = document.getElementById("crop-modal");
        const preview = document.getElementById("crop-preview");
        const confirmBtn = document.getElementById("crop-confirm");

        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            modal.classList.remove("hidden");

            if (cropper) cropper.destroy();
            cropper = new Cropper(preview, {
                aspectRatio: 1,
                viewMode: 1,
                autoCropArea: 0.9,
                responsive: true,
                background: false,
            });
        };
        reader.readAsDataURL(file);

        confirmBtn.onclick = () => {
            const canvas = cropper.getCroppedCanvas({
                width: 512,
                height: 512,
                imageSmoothingEnabled: true,
                imageSmoothingQuality: "high",
            });
            canvas.toBlob((blob) => {
                croppedBlob = blob;
                modal.classList.add("hidden");
                cropper.destroy();
                cropper = null;

                const nameInput = document.querySelector('input[name="name"]');
                if (!nameInput.value && file.name) {
                    nameInput.value = file.name.replace(/\.[^.]+$/, "").slice(0, 30);
                }

                const thumb = document.getElementById("crop-thumb");
                const thumbWrap = document.getElementById("crop-thumb-wrap");
                thumb.src = URL.createObjectURL(blob);
                thumbWrap.classList.remove("hidden");

                const hint = document.getElementById("crop-hint");
                if (hint) hint.classList.add("hidden");
            }, "image/jpeg", 0.92);
        };
    }

    function getCroppedFile(filename) {
        if (!croppedBlob) return null;
        return new File([croppedBlob], filename || "crop.jpg", { type: "image/jpeg" });
    }

    function reset() {
        croppedBlob = null;
        const thumbWrap = document.getElementById("crop-thumb-wrap");
        if (thumbWrap) thumbWrap.classList.add("hidden");
        const hint = document.getElementById("crop-hint");
        if (hint) hint.classList.remove("hidden");
    }

    return { showModal, getCroppedFile, reset };
})();