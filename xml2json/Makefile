#CXX = 

UNAME := $(shell uname -s)
ifeq ($(UNAME), Darwin)
LINKOPTIONS = -Wl,-search_paths_first -Wl,-dead_strip -v
else
    ifdef DEBUG
	LINKOPTIONS = -Wl,--gc-sections
    else
	LINKOPTIONS = -Wl,--gc-sections -Wl,--strip-all
    endif
endif

INCLUDE += -I./include/
ifdef DEBUG
    COMPILEOPTIONS  = -std=c++11 -O0 -ggdb -g3 -fdata-sections -ffunction-sections
    WARNINGS = -Wall
else
    COMPILEOPTIONS  = -std=c++11 -O3 -fdata-sections -ffunction-sections
    WARNINGS = -Wall -Wextra -Werror
endif

MAIN 	= xml2json.o
OBJECTS = xml2json.gch
EXEC 	= xml2json

#############################################################

all : ${EXEC}

shared : ${EXEC}

xml2json.gch : include/xml2json.hpp
	${CXX} ${COMPILEOPTIONS}  -c $< -o $@

${MAIN} : xml2json.cpp
	${CXX} ${COMPILEOPTIONS} $(INCLUDE) -c $< -o $@

${EXEC} : ${MAIN} ${OBJECTS}
	${CXX} ${LINKOPTIONS} ${MAIN} -o ${EXEC}

clean :
	rm *.gch *.o ${EXEC}
