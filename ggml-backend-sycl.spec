# Intel GPU plugin for the system ggml package.
# Built on its own: the ggml package's PGO build already fills the ABF
# timeout, and icpx cannot share a compiler with the HIP backend.
# The plugin matches ggml %{version} (same tarball and the same ABI patches).

%global _disable_lto 1
%global debug_package %{nil}
%global optflags %{optflags} -O3
%global backend_dir %{_libdir}/ggml-backends-%{version}

Name:		ggml-backend-sycl
Version:	0.25.1
Release:	1
Summary:	Intel GPU SYCL backend plugin for ggml
Group:		System/Libraries
License:	MIT
URL:		https://github.com/ggml-org/ggml
Source0:	https://github.com/ggml-org/ggml/archive/refs/tags/v%{version}/ggml-%{version}.tar.gz
Patch0:		0001-llvm23-bf16-wmma-short-vectors.patch
Patch1:		0002-backend-dl-quantize-tests.patch
Patch2:		0003-test-backend-ops-case-counter.patch
Patch3:		0004-max-name-160-and-i8-convrot.patch
Patch4:		0005-solve-tri-trsm-loop.patch
Patch5:		0006-sycl-device-skip-arm-neon.patch


BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	clang
BuildRequires:	intel-llvm
BuildRequires:	onemath-devel
BuildRequires:	onednn-devel
BuildRequires:	pkgconfig(level-zero) >= 1.32.0
BuildRequires:	opencl-headers

Requires:	%{mklibname ggml}%{?_isa} >= %{version}

%description
ggml backend plugin for Intel GPUs. It is built with the DPC++ compiler
(icpx), Level Zero, oneMath's generic SYCL BLAS and oneDNN's Intel GPU
kernels.

oneMath's generic BLAS is the open-source stand-in for oneMKL. It is
correct across shapes; oneDNN covers the large matmul and attention
calls. Together this is the Intel counterpart of the ROCm/HIP backend.

%prep
%autosetup -n ggml-%{version} -p1

%build
# Host -march and -flto from the distro flags break icpx device compilation.
_flags=$(printf '%s' "%{optflags}" | sed -E 's/-flto//g; s/-g3//g; s/-gdwarf-4//g; s/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
# icpx does not search /usr/include, and its sycl headers include CL/cl.h.
_flags="$_flags -g0 -I%{_includedir}"
_ldflags=$(printf '%s' "%{build_ldflags}" | sed -E 's/-flto//g; s/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CFLAGS="$_flags"
export CXXFLAGS="$_flags"
export LDFLAGS="$_ldflags"
export CC=clang
# icpx compiles C++, but a link of .o files only does not pull in libstdc++.
mkdir -p %{_builddir}/bin
cat > %{_builddir}/bin/icpx << EOF
#!/bin/sh
link=1
for arg in "\$@"; do
	case "\$arg" in
	-c|-E|-S|-fsyntax-only) link=0 ;;
	esac
done
if [ "\$link" = 1 ]; then
	exec %{_libdir}/intel-llvm/bin/icpx "\$@" -lstdc++
else
	exec %{_libdir}/intel-llvm/bin/icpx "\$@"
fi
EOF
chmod 755 %{_builddir}/bin/icpx
export CXX="%{_builddir}/bin/icpx"
export CMAKE_GENERATOR=Ninja
%cmake \
	-DGGML_NATIVE:BOOL=OFF \
	-DGGML_LTO:BOOL=OFF \
	-DGGML_OPENMP:BOOL=OFF \
	-DGGML_BACKEND_DL:BOOL=ON \
	-DGGML_BACKEND_DIR=%{backend_dir} \
	-DGGML_CPU:BOOL=ON \
	-DGGML_CPU_ALL_VARIANTS:BOOL=OFF \
	-DGGML_AVX:BOOL=OFF \
	-DGGML_AVX2:BOOL=OFF \
	-DGGML_AVX512:BOOL=OFF \
	-DGGML_VULKAN:BOOL=OFF \
	-DGGML_OPENCL:BOOL=OFF \
	-DGGML_BLAS:BOOL=OFF \
	-DGGML_HIP:BOOL=OFF \
	-DGGML_CUDA:BOOL=OFF \
	-DGGML_METAL:BOOL=OFF \
	-DGGML_RPC:BOOL=OFF \
	-DGGML_BUILD_TESTS:BOOL=OFF \
	-DGGML_BUILD_EXAMPLES:BOOL=OFF \
	-DGGML_SYCL:BOOL=ON \
	-DGGML_SYCL_TARGET=INTEL \
	-DGGML_SYCL_F16:BOOL=ON \
	-DGGML_SYCL_DNN:BOOL=ON \
	-DGGML_SYCL_SUPPORT_LEVEL_ZERO_API:BOOL=ON \
	-DCMAKE_INSTALL_RPATH=%{_libdir}/intel-llvm/lib
ninja -v

%install
_so=$(find build -name 'libggml-sycl.so' -print -quit)
test -n "$_so"
mkdir -p %{buildroot}%{backend_dir}
install -pm 755 "$_so" %{buildroot}%{backend_dir}/libggml-sycl.so

%files
%license LICENSE
%dir %{backend_dir}
%{backend_dir}/libggml-sycl.so
